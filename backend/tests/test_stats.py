from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.models import ScanRecord, Officer
from app.db.scan_repository import ScanRepository
from app.db.session import get_db
from app.services.stats_service import StatsService
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


# 1. Test Empty Database Dashboard Statistics
def test_empty_dashboard_stats(in_memory_db):
    service = StatsService()
    stats = service.get_dashboard_statistics(db=in_memory_db)

    assert stats["summary"]["total_scans"] == 0
    assert stats["summary"]["compliance_rate"] == 0.0
    assert stats["summary"]["average_compliance_score"] == 0.0
    assert isinstance(stats["violation_rate_by_field"], list)
    assert stats["violation_trend_over_time"] == []
    assert stats["top_non_compliant_brands"] == []
    assert stats["authenticity_flag_rate"]["total_scans_evaluated"] == 0
    assert stats["font_size_distribution"]["total_regions_evaluated"] == 0


# 2. Test Full Dashboard Analytics with Synthetic Data
def test_full_dashboard_analytics(in_memory_db):
    service = StatsService()

    base_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)

    # Scan 1: Brand Alpha - Fully Compliant (2026-08-01)
    s1 = ScanRecord(
        product_name="Brand Alpha Cookies",
        overall_status="COMPLIANT",
        compliance_score=100.0,
        compliance_result={
            "overall_status": "COMPLIANT",
            "compliance_score": 100.0,
            "results": [
                {"rule_id": "LMPC_RULE_6_1_E", "declaration": "MRP", "status": "PASS", "evidence": {"pixel_text_height": 18.0}},
                {"rule_id": "LMPC_RULE_6_1_C", "declaration": "Net Quantity", "status": "PASS", "evidence": {"pixel_text_height": 14.0}},
                {"rule_id": "LMPC_RULE_6_1_A", "declaration": "Manufacturer", "status": "PASS", "evidence": {"pixel_text_height": 10.0}}
            ]
        },
        authenticity_result={
            "similarity_score": 0.94,
            "verdict": "GENUINE_LIKELY"
        },
        created_at=base_time
    )

    # Scan 2: Brand Beta - Non-Compliant (MRP & Qty missing, tiny font) (2026-08-01)
    s2 = ScanRecord(
        product_name="Brand Beta Juice",
        overall_status="NON_COMPLIANT",
        compliance_score=35.0,
        compliance_result={
            "overall_status": "NON_COMPLIANT",
            "compliance_score": 35.0,
            "results": [
                {"rule_id": "LMPC_RULE_6_1_E", "declaration": "MRP", "status": "FAIL", "evidence": {"pixel_text_height": 6.5}},
                {"rule_id": "LMPC_RULE_6_1_C", "declaration": "Net Quantity", "status": "FAIL", "evidence": {"pixel_text_height": 7.0}},
                {"rule_id": "LMPC_RULE_6_1_A", "declaration": "Manufacturer", "status": "PASS", "evidence": {"pixel_text_height": 32.0}}
            ]
        },
        authenticity_result={
            "similarity_score": 0.42,
            "verdict": "SUSPICIOUS"
        },
        created_at=base_time + timedelta(hours=2)
    )

    # Scan 3: Brand Beta - Another Non-Compliant scan (2026-08-02)
    s3 = ScanRecord(
        product_name="Brand Beta Juice",
        overall_status="NON_COMPLIANT",
        compliance_score=50.0,
        compliance_result={
            "overall_status": "NON_COMPLIANT",
            "compliance_score": 50.0,
            "results": [
                {"rule_id": "LMPC_RULE_6_1_E", "declaration": "MRP", "status": "FAIL", "evidence": {"pixel_text_height": 10.0}},
                {"rule_id": "LMPC_RULE_6_1_C", "declaration": "Net Quantity", "status": "PASS", "evidence": {"pixel_text_height": 15.0}},
                {"rule_id": "LMPC_RULE_6_1_D", "declaration": "Date of Packing", "status": "WARNING", "evidence": {"pixel_text_height": 11.0}}
            ]
        },
        authenticity_result={
            "similarity_score": 0.51,
            "verdict": "SUSPICIOUS"
        },
        created_at=base_time + timedelta(days=1)
    )

    # Scan 4: Brand Gamma - No reference available (2026-08-03)
    s4 = ScanRecord(
        product_name="Brand Gamma Spices",
        overall_status="COMPLIANT",
        compliance_score=90.0,
        compliance_result={
            "overall_status": "COMPLIANT",
            "compliance_score": 90.0,
            "results": [
                {"rule_id": "LMPC_RULE_6_1_E", "declaration": "MRP", "status": "PASS", "evidence": {"pixel_text_height": 20.0}},
                {"rule_id": "LMPC_RULE_6_1_C", "declaration": "Net Quantity", "status": "PASS", "evidence": {"pixel_text_height": 20.0}}
            ]
        },
        authenticity_result={
            "similarity_score": 0.0,
            "verdict": "NO_REFERENCE_AVAILABLE"
        },
        created_at=base_time + timedelta(days=2)
    )

    in_memory_db.add_all([s1, s2, s3, s4])
    in_memory_db.commit()

    stats = service.get_dashboard_statistics(db=in_memory_db)

    # 1. Summary assertions
    assert stats["summary"]["total_scans"] == 4
    assert stats["summary"]["compliant_scans"] == 2
    assert stats["summary"]["non_compliant_scans"] == 2
    assert stats["summary"]["compliance_rate"] == 50.0
    assert stats["summary"]["average_compliance_score"] == round((100.0 + 35.0 + 50.0 + 90.0) / 4.0, 2)

    # 2. Violation Rate by Field assertions
    fields_dict = {f["field_name"]: f for f in stats["violation_rate_by_field"]}
    assert "mrp" in fields_dict
    assert fields_dict["mrp"]["rule_id"] == "LMPC_RULE_6_1_E"
    assert fields_dict["mrp"]["violation_count"] == 2  # s2, s3 failed
    assert fields_dict["mrp"]["total_evaluations"] == 4
    assert fields_dict["mrp"]["violation_rate"] == 50.0

    assert "net_quantity" in fields_dict
    assert fields_dict["net_quantity"]["violation_count"] == 1  # s2 failed
    assert fields_dict["net_quantity"]["total_evaluations"] == 4

    # 3. Violation Trend Over Time assertions
    trends = stats["violation_trend_over_time"]
    assert len(trends) == 3  # 2026-08-01, 2026-08-02, 2026-08-03
    assert trends[0]["date"] == "2026-08-01"
    assert trends[0]["total_scans"] == 2
    assert trends[0]["compliant_scans"] == 1
    assert trends[0]["non_compliant_scans"] == 1

    assert trends[1]["date"] == "2026-08-02"
    assert trends[1]["total_scans"] == 1
    assert trends[1]["non_compliant_scans"] == 1

    # 4. Top Non-Compliant Brands assertions
    top_brands = stats["top_non_compliant_brands"]
    assert len(top_brands) >= 1
    assert top_brands[0]["brand_name"] == "Brand Beta Juice"
    assert top_brands[0]["total_scans"] == 2
    assert top_brands[0]["non_compliant_scans"] == 2
    assert top_brands[0]["non_compliance_rate"] == 100.0
    assert top_brands[0]["most_common_violation"] == "MRP"

    # 5. Authenticity Flag Rate assertions
    auth_stats = stats["authenticity_flag_rate"]
    assert auth_stats["total_scans_evaluated"] == 4
    assert auth_stats["genuine_count"] == 1
    assert auth_stats["suspicious_count"] == 2
    assert auth_stats["no_reference_count"] == 1
    assert auth_stats["suspicious_flag_rate"] == 50.0  # 2 out of 4

    # 6. Font Size Distribution assertions
    font_stats = stats["font_size_distribution"]
    dist = font_stats["distribution"]
    assert dist["under_8px"] == 2  # 6.5px, 7.0px from s2
    assert dist["between_8_12px"] == 3  # 10.0px (s1), 10.0px (s3), 11.0px (s3)
    assert dist["between_12_24px"] == 5  # 18px (s1), 14px (s1), 15px (s3), 20px (s4), 20px (s4)
    assert dist["over_24px"] == 1  # 32px (s2)
    assert font_stats["total_regions_evaluated"] == 11
    assert font_stats["average_text_height_px"] > 0.0


# 3. Test Date-Range Filtering
def test_dashboard_date_range_filtering(in_memory_db):
    service = StatsService()

    d1 = datetime(2026, 7, 10, tzinfo=timezone.utc)
    d2 = datetime(2026, 7, 20, tzinfo=timezone.utc)
    d3 = datetime(2026, 7, 30, tzinfo=timezone.utc)

    in_memory_db.add_all([
        ScanRecord(product_name="July 10 Scan", overall_status="COMPLIANT", compliance_score=100.0, compliance_result={}, created_at=d1),
        ScanRecord(product_name="July 20 Scan", overall_status="NON_COMPLIANT", compliance_score=50.0, compliance_result={}, created_at=d2),
        ScanRecord(product_name="July 30 Scan", overall_status="COMPLIANT", compliance_score=95.0, compliance_result={}, created_at=d3)
    ])
    in_memory_db.commit()

    # Filter only July 15 to July 25
    filtered_stats = service.get_dashboard_statistics(
        db=in_memory_db,
        start_date="2026-07-15",
        end_date="2026-07-25"
    )

    assert filtered_stats["summary"]["total_scans"] == 1
    assert filtered_stats["summary"]["non_compliant_scans"] == 1
    assert filtered_stats["violation_trend_over_time"][0]["date"] == "2026-07-20"


# 4. Test FastAPI GET /api/stats/dashboard Endpoint
def test_api_stats_dashboard_endpoint(in_memory_db):
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_officer] = lambda: Officer(id=1, username="test_inspector", role="inspector", is_active=True)


    # Seed one record
    in_memory_db.add(
        ScanRecord(
            product_name="API Demo Product",
            overall_status="COMPLIANT",
            compliance_score=98.0,
            compliance_result={
                "overall_status": "COMPLIANT",
                "compliance_score": 98.0,
                "results": [{"rule_id": "LMPC_RULE_6_1_E", "declaration": "MRP", "status": "PASS"}]
            }
        )
    )
    in_memory_db.commit()

    try:
        resp = client.get("/api/stats/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "violation_rate_by_field" in data
        assert "violation_trend_over_time" in data
        assert "top_non_compliant_brands" in data
        assert "authenticity_flag_rate" in data
        assert "font_size_distribution" in data
        assert data["summary"]["total_scans"] == 1

        # Test with date filters
        resp_filtered = client.get("/api/stats/dashboard?start_date=2026-01-01&end_date=2026-12-31")
        assert resp_filtered.status_code == 200
        assert resp_filtered.json()["summary"]["total_scans"] == 1
    finally:
        app.dependency_overrides.clear()
