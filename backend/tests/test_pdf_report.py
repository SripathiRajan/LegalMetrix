import io
import base64
import numpy as np
import cv2
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.models import ScanRecord, Officer
from app.db.scan_repository import ScanRepository
from app.db.session import get_db
from app.services.pdf_report_generator import PDFReportGenerator
from app.auth.dependencies import get_current_active_officer
from app.main import app


client = TestClient(app)


@pytest.fixture
def in_memory_db():
    """Sets up an isolated in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _generate_dummy_b64_image() -> str:
    """Creates a small 60x60 BGR image and converts to base64 Data URI."""
    img = np.zeros((60, 60, 3), dtype=np.uint8)
    cv2.rectangle(img, (10, 10), (50, 50), (0, 255, 0), -1)
    _, buf = cv2.imencode(".png", img)
    b64_str = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


# 1. Test PDFReportGenerator Generation & PDF Header
def test_pdf_report_generator_basic():
    generator = PDFReportGenerator()

    compliance_result = {
        "overall_status": "COMPLIANT",
        "compliance_score": 96.5,
        "total_checks": 8,
        "passed": 8,
        "failed": 0,
        "warnings": 0,
        "results": [
            {
                "rule_id": "LMPC_RULE_6_1_E",
                "declaration": "Maximum Retail Price (MRP)",
                "status": "PASS",
                "detected_value": "₹150.00 incl. of all taxes",
                "reason": "MRP correctly declared with inclusive of all taxes"
            },
            {
                "rule_id": "LMPC_RULE_6_1_C",
                "declaration": "Net Quantity",
                "status": "PASS",
                "detected_value": "500 g",
                "reason": "Standard SI unit declared"
            }
        ]
    }

    authenticity_result = {
        "verdict": "GENUINE_LIKELY",
        "similarity_score": 0.945,
        "threshold_used": 0.80,
        "notes": "Packaging visual embeddings match reference brand perfectly.",
        "brand_name": "Premium Tea Ltd"
    }

    pdf_bytes = generator.generate_report(
        compliance_result=compliance_result,
        scan_id=101,
        product_name="Premium Black Tea 500g",
        officer_id="INSP_042",
        created_at=datetime(2026, 8, 15, 14, 30, 0, tzinfo=timezone.utc),
        annotated_image_b64=_generate_dummy_b64_image(),
        authenticity_result=authenticity_result
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


# 2. Test PDF Generation with Mixed Violations and Warnings
def test_pdf_report_generator_mixed_violations():
    generator = PDFReportGenerator()

    compliance_result = {
        "overall_status": "NON_COMPLIANT",
        "compliance_score": 45.0,
        "total_checks": 4,
        "passed": 1,
        "failed": 2,
        "warnings": 1,
        "results": [
            {
                "rule_id": "LMPC_RULE_6_1_E",
                "declaration": "MRP",
                "status": "FAIL",
                "detected_value": None,
                "reason": "MRP declaration missing from principal display panel"
            },
            {
                "rule_id": "LMPC_RULE_6_1_C",
                "declaration": "Net Quantity",
                "status": "FAIL",
                "detected_value": "100 gms",
                "reason": "Non-standard abbreviation 'gms' used instead of 'g'"
            },
            {
                "rule_id": "LMPC_RULE_6_1_D",
                "declaration": "Date of Manufacture",
                "status": "WARNING",
                "detected_value": "2026",
                "reason": "Month missing from date declaration"
            },
            {
                "rule_id": "LMPC_RULE_6_1_A",
                "declaration": "Manufacturer Details",
                "status": "PASS",
                "detected_value": "ABC Corp, Mumbai 400001",
                "reason": "Complete name and postal address found"
            }
        ]
    }

    authenticity_result = {
        "verdict": "SUSPICIOUS",
        "similarity_score": 0.42,
        "threshold_used": 0.80,
        "notes": "Color palette mismatch and altered logo typeface.",
        "brand_name": "ABC Corp"
    }

    pdf_bytes = generator.generate_report(
        compliance_result=compliance_result,
        scan_id=102,
        product_name="Counterfeit Snack Pack",
        authenticity_result=authenticity_result
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


# 3. Test API Streaming Endpoint GET /api/scans/{id}/report.pdf
def test_api_download_pdf_report(in_memory_db):
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_officer] = lambda: Officer(id=1, username="test_inspector", role="inspector", is_active=True)


    # Seed a persistent scan
    record = ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result={
            "overall_status": "COMPLIANT",
            "compliance_score": 98.0,
            "total_checks": 2,
            "passed": 2,
            "failed": 0,
            "warnings": 0,
            "results": [
                {
                    "rule_id": "LMPC_RULE_6_1_E",
                    "declaration": "MRP",
                    "status": "PASS",
                    "detected_value": "₹45.00",
                    "reason": "Valid MRP"
                }
            ],
            "annotated_image": _generate_dummy_b64_image()
        },
        product_name="Organic Basmati Rice",
        overall_status="COMPLIANT",
        compliance_score=98.0
    )

    try:
        # Successful PDF download
        resp = client.get(f"/api/scans/{record.id}/report.pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert f"filename=\"legal_metrology_report_scan_{record.id}.pdf\"" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF-")

        # 404 for non-existent scan
        resp_404 = client.get("/api/scans/99999/report.pdf")
        assert resp_404.status_code == 404
    finally:
        app.dependency_overrides.clear()
