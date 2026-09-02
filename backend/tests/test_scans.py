import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.models import ScanRecord, Officer
from app.db.scan_repository import ScanRepository
from app.db.session import get_db
from app.services.history_service import HistoryService
from app.services.compliance_service import ComplianceService
from app.ocr.ocr_engine import MockOCREngine
from app.models.extracted_product import OCRResult, OCRRegion
from app.auth.dependencies import get_current_active_officer
from app.main import app



from sqlalchemy.pool import StaticPool

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



# 1. Test ScanRepository CRUD & Field Integrity
def test_scan_repository_crud(in_memory_db):
    compliance_payload = {
        "overall_status": "COMPLIANT",
        "compliance_score": 95.5,
        "total_checks": 10,
        "passed": 9,
        "failed": 0,
        "warnings": 1,
        "human_verification_required": 0,
        "not_applicable": 0,
        "violations": []
    }
    extracted_payload = {
        "product_name": {"value": "Organic Wheat Flour", "is_detected": True},
        "mrp": {"value": "₹85.00", "is_detected": True},
        "net_quantity": {"value": "1 kg", "is_detected": True}
    }
    authenticity_payload = {
        "similarity_score": 0.92,
        "verdict": "GENUINE_LIKELY",
        "threshold_used": 0.80
    }
    visual_stats = {
        "average_confidence": 0.96,
        "regions_detected": 5
    }

    record = ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result=compliance_payload,
        extracted_data=extracted_payload,
        authenticity_result=authenticity_payload,
        visual_statistics=visual_stats,
        image_path="/uploads/wheat_flour.png",
        product_name="Organic Wheat Flour",
        overall_status="COMPLIANT",
        compliance_score=95.5
    )

    assert record.id is not None
    assert record.product_name == "Organic Wheat Flour"
    assert record.overall_status == "COMPLIANT"
    assert record.compliance_score == 95.5
    assert record.compliance_result["passed"] == 9
    assert record.authenticity_result["verdict"] == "GENUINE_LIKELY"

    # Get by ID
    fetched = ScanRepository.get_scan(in_memory_db, record.id)
    assert fetched is not None
    assert fetched.id == record.id
    assert fetched.product_name == "Organic Wheat Flour"


# 2. Test ScanRepository Listing, Filters, Pagination, and Aggregates
def test_scan_repository_list_and_aggregates(in_memory_db):
    # Seed 3 records
    ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result={"overall_status": "COMPLIANT", "compliance_score": 100.0},
        product_name="Brand A Biscuits",
        overall_status="COMPLIANT",
        compliance_score=100.0
    )
    ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result={"overall_status": "NON_COMPLIANT", "compliance_score": 40.0},
        product_name="Brand B Juice",
        overall_status="NON_COMPLIANT",
        compliance_score=40.0
    )
    ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result={"overall_status": "COMPLIANT", "compliance_score": 90.0},
        product_name="Brand C Oil",
        overall_status="COMPLIANT",
        compliance_score=90.0
    )

    # List all
    records, total = ScanRepository.list_scans(in_memory_db, limit=10, offset=0)
    assert total == 3
    assert len(records) == 3

    # Filter by status
    compliant_records, comp_total = ScanRepository.list_scans(in_memory_db, status="COMPLIANT")
    assert comp_total == 2
    assert all(r.overall_status == "COMPLIANT" for r in compliant_records)

    # Filter by product name partial match
    juice_records, juice_total = ScanRepository.list_scans(in_memory_db, product_name="Juice")
    assert juice_total == 1
    assert juice_records[0].product_name == "Brand B Juice"

    # Pagination
    paged_records, _ = ScanRepository.list_scans(in_memory_db, limit=2, offset=0)
    assert len(paged_records) == 2

    # Aggregates
    stats = ScanRepository.get_compliance_aggregates(in_memory_db)
    assert stats["total_scans"] == 3
    assert stats["compliant_count"] == 2
    assert stats["non_compliant_count"] == 1
    assert stats["compliance_rate"] == round((2 / 3) * 100.0, 2)
    assert stats["average_score"] == round((100.0 + 40.0 + 90.0) / 3.0, 2)


# 3. Test HistoryService Wrapper
def test_history_service(in_memory_db):
    service = HistoryService()

    record = service.record_scan(
        compliance_result={"overall_status": "COMPLIANT", "compliance_score": 98.0},
        extracted_data={"product_name": {"value": "Pure Ghee"}},
        db=in_memory_db
    )
    assert record.id is not None

    res = service.list_scans(db=in_memory_db)
    assert res["total"] == 1
    assert res["items"][0]["product_name"] == "Pure Ghee"

    metrics = service.get_dashboard_metrics(db=in_memory_db)
    assert metrics["total_scans"] == 1
    assert metrics["compliance_rate"] == 100.0


# 4. Test FastAPI GET /api/scans and GET /api/scans/{id} Endpoints
def test_api_scans_endpoints(in_memory_db):
    # Override get_db dependency to use our in-memory SQLite database
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_officer] = lambda: Officer(id=1, username="test_inspector", role="inspector", is_active=True)


    # Seed test record
    record = ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result={"overall_status": "COMPLIANT", "compliance_score": 96.0},
        product_name="Honey 500g",
        overall_status="COMPLIANT",
        compliance_score=96.0
    )

    try:
        # GET /api/scans
        resp = client.get("/api/scans")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["product_name"] == "Honey 500g"

        # GET /api/scans/{id}
        resp_single = client.get(f"/api/scans/{record.id}")
        assert resp_single.status_code == 200
        single_data = resp_single.json()
        assert single_data["id"] == record.id
        assert single_data["product_name"] == "Honey 500g"

        # GET /api/scans/99999 (Not Found)
        resp_404 = client.get("/api/scans/99999")
        assert resp_404.status_code == 404

        # GET /api/scans/stats/summary
        resp_stats = client.get("/api/scans/stats/summary")
        assert resp_stats.status_code == 200
        assert resp_stats.json()["total_scans"] == 1
    finally:
        app.dependency_overrides.clear()


# 5. Test ComplianceService End-to-End with persist=True
def test_compliance_service_persist(in_memory_db):
    history_svc = HistoryService()
    mock_ocr = MockOCREngine(OCRResult(
        raw_text="Test Brand Biscuits\nMRP ₹50.00 incl. of all taxes\nNet Qty: 100 g\nCountry of Origin: India\nMfg by: Test Ltd, Chennai 600001\nConsumer Care: care@test.com 1800-111-2222\nPkd: 05/2026",
        regions=[
            OCRRegion(text="Test Brand Biscuits", confidence=0.98, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]]),
            OCRRegion(text="MRP ₹50.00 incl. of all taxes", confidence=0.96, bounding_box=[[0, 20], [10, 20], [10, 30], [0, 30]]),
            OCRRegion(text="Net Qty: 100 g", confidence=0.97, bounding_box=[[0, 40], [10, 40], [10, 50], [0, 50]]),
            OCRRegion(text="Country of Origin: India", confidence=0.99, bounding_box=[[0, 60], [10, 60], [10, 70], [0, 70]]),
            OCRRegion(text="Mfg by: Test Ltd, Chennai 600001", confidence=0.95, bounding_box=[[0, 80], [10, 80], [10, 90], [0, 90]]),
            OCRRegion(text="Consumer Care: care@test.com 1800-111-2222", confidence=0.96, bounding_box=[[0, 100], [10, 100], [10, 110], [0, 110]]),
            OCRRegion(text="Pkd: 05/2026", confidence=0.95, bounding_box=[[0, 120], [10, 120], [10, 130], [0, 130]])
        ],
        average_confidence=0.965
    ))

    comp_svc = ComplianceService(ocr_engine=mock_ocr, history_service=history_svc)

    # Synthesize dummy bytes
    import numpy as np
    import cv2
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", dummy_img)
    img_bytes = buf.tobytes()

    # Pass in-memory session by temporarily patching SessionLocal or record_scan
    original_save = ScanRepository.save_scan
    saved_records = []

    def mock_save(*args, **kwargs):
        kwargs["db"] = in_memory_db
        rec = original_save(*args, **kwargs)
        saved_records.append(rec)
        return rec

    ScanRepository.save_scan = staticmethod(mock_save)

    try:
        response = comp_svc.analyze_image_end_to_end(
            img_bytes,
            multi_pass=False,
            persist=True
        )
        assert len(saved_records) == 1
        assert saved_records[0].id is not None
        assert saved_records[0].overall_status == "COMPLIANT"
    finally:
        ScanRepository.save_scan = staticmethod(original_save)
