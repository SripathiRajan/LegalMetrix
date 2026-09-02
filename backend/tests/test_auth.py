import pytest
import io
import numpy as np
import cv2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from jose import jwt

from app.db.base import Base
from app.db.models import Officer, ScanRecord
from app.db.scan_repository import ScanRepository
from app.db.session import get_db
from app.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    SECRET_KEY,
    ALGORITHM
)
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


# 1. Test Password Cryptography & JWT Token Generation
def test_password_hashing_and_jwt_tokens():
    raw_pass = "InspectorSecret2026!"
    hashed = get_password_hash(raw_pass)

    assert verify_password(raw_pass, hashed)
    assert not verify_password("WrongPassword123", hashed)

    # JWT Creation and Decoding
    claims = {"sub": "inspector_rajesh", "officer_id": 42, "role": "inspector"}
    token = create_access_token(claims)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded["sub"] == "inspector_rajesh"
    assert decoded["officer_id"] == 42
    assert decoded["role"] == "inspector"


# 2. Test Register, Login, and Profile (/api/auth/me) Endpoints
def test_officer_register_and_login_flow(in_memory_db):
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        # Register new officer
        reg_payload = {
            "username": "officer_sharma",
            "email": "sharma@consumer.gov.in",
            "password": "SecurePassword123",
            "badge_number": "LM-DELHI-007",
            "role": "inspector"
        }
        reg_resp = client.post("/api/auth/register", json=reg_payload)
        assert reg_resp.status_code == 201
        reg_data = reg_resp.json()
        assert reg_data["username"] == "officer_sharma"
        assert reg_data["badge_number"] == "LM-DELHI-007"
        assert "password" not in reg_data

        # Duplicate register should fail
        dup_resp = client.post("/api/auth/register", json=reg_payload)
        assert dup_resp.status_code == 400

        # Login with correct password
        login_resp = client.post("/api/auth/login", json={
            "username": "officer_sharma",
            "password": "SecurePassword123"
        })
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["officer"]["username"] == "officer_sharma"

        token = token_data["access_token"]

        # Login with invalid password
        bad_login = client.post("/api/auth/login", json={
            "username": "officer_sharma",
            "password": "IncorrectPassword"
        })
        assert bad_login.status_code == 401

        # Access /api/auth/me with Bearer token
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "officer_sharma"
    finally:
        app.dependency_overrides.clear()


# 3. Test Protected Endpoints Deny Unauthenticated Requests (401)
def test_protected_endpoints_require_auth(in_memory_db):
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        # 1. GET /api/scans
        resp = client.get("/api/scans")
        assert resp.status_code == 401

        # 2. GET /api/scans/1
        resp = client.get("/api/scans/1")
        assert resp.status_code == 401

        # 3. GET /api/scans/1/report.pdf
        resp = client.get("/api/scans/1/report.pdf")
        assert resp.status_code == 401

        # 4. GET /api/scans/stats/summary
        resp = client.get("/api/scans/stats/summary")
        assert resp.status_code == 401

        # 5. GET /api/stats/dashboard
        resp = client.get("/api/stats/dashboard")
        assert resp.status_code == 401

        # 6. POST /api/chatbot/query
        resp = client.post("/api/chatbot/query", json={"query": "What is Rule 6(1)(e)?"})
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


# 4. Test Protected Endpoints Succeed with Valid Bearer Token
def test_protected_endpoints_with_valid_token(in_memory_db):
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Register officer
    hashed = get_password_hash("InspectPass123")
    officer = Officer(username="test_inspector", hashed_password=hashed, role="inspector", is_active=True)
    in_memory_db.add(officer)

    # Seed scan record
    scan = ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result={"overall_status": "COMPLIANT", "compliance_score": 95.0, "results": []},
        product_name="Authorized Wheat Pack",
        overall_status="COMPLIANT",
        compliance_score=95.0
    )
    in_memory_db.commit()

    token = create_access_token({"sub": "test_inspector", "officer_id": officer.id, "role": "inspector"})
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # GET /api/scans
        resp_scans = client.get("/api/scans", headers=headers)
        assert resp_scans.status_code == 200
        assert resp_scans.json()["total"] == 1

        # GET /api/scans/{id}
        resp_scan = client.get(f"/api/scans/{scan.id}", headers=headers)
        assert resp_scan.status_code == 200
        assert resp_scan.json()["product_name"] == "Authorized Wheat Pack"

        # GET /api/stats/dashboard
        resp_dash = client.get("/api/stats/dashboard", headers=headers)
        assert resp_dash.status_code == 200
        assert resp_dash.json()["summary"]["total_scans"] == 1

        # GET /api/scans/{id}/report.pdf
        resp_pdf = client.get(f"/api/scans/{scan.id}/report.pdf", headers=headers)
        assert resp_pdf.status_code == 200
        assert resp_pdf.headers["content-type"] == "application/pdf"

        # POST /api/chatbot/query
        resp_bot = client.post("/api/chatbot/query", json={"query": "mrp declaration rule", "top_k": 2}, headers=headers)
        assert resp_bot.status_code == 200
        assert resp_bot.json()["query"] == "mrp declaration rule"
    finally:
        app.dependency_overrides.clear()


# 5. Verify Public Scanning Endpoints Remain Unauthenticated
def test_public_scanning_endpoints_unauthenticated():
    # 1. GET /
    health = client.get("/")
    assert health.status_code == 200

    # 2. POST /api/compliance/check
    check_payload = {
        "product_name": "Public Biscuit",
        "generic_name": "Biscuits",
        "mrp": "MRP Rs. 20.00 incl. of all taxes",
        "net_quantity": "100 g",
        "date_declaration": "08/2026",
        "manufacturer_name": "Public Foods Ltd",
        "manufacturer_address": "Plot 12, Sector 4, Mumbai, Maharashtra - 400001",
        "consumer_care": "care@publicfoods.com, 1800-111-222, Mumbai",
        "consumer_care_email": "care@publicfoods.com",
        "consumer_care_phone": "1800-111-222",
        "country_of_origin": "India",
        "is_imported": False
    }
    check_resp = client.post("/api/compliance/check", json=check_payload)
    assert check_resp.status_code == 200
    assert check_resp.json()["overall_status"] == "COMPLIANT"



    # 3. POST /api/analyze with dummy image
    dummy_img = np.zeros((80, 80, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", dummy_img)
    files = {"file": ("package.png", buf.tobytes(), "image/png")}
    
    analyze_resp = client.post("/api/analyze", files=files)
    assert analyze_resp.status_code == 200
    assert "compliance_result" in analyze_resp.json()
