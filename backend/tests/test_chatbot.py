import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.models import Officer, ScanRecord
from app.db.scan_repository import ScanRepository
from app.db.session import get_db
from app.auth.security import get_password_hash, create_access_token
from app.auth.dependencies import get_current_active_officer
from app.chatbot.query_router import QueryRouter
from app.chatbot.schemas import QueryIntent
from app.chatbot.service import GroundedChatbotService, STANDARD_REFUSAL_MESSAGE
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


# 1. Test Deterministic Query Router Intent Classification
def test_query_router_classification():
    router = QueryRouter()

    # Rule Lookups
    assert router.classify("What is Rule 6(1)(e) regarding Maximum Retail Price?") == QueryIntent.RULE_LOOKUP
    assert router.classify("Tell me about net quantity requirements under LMPC rules") == QueryIntent.RULE_LOOKUP
    assert router.classify("निर्माता का नाम और पता नियम 2011") == QueryIntent.RULE_LOOKUP

    # Data Queries
    assert router.classify("How many scans are in the database?") == QueryIntent.DATA_QUERY
    assert router.classify("What is the overall compliance rate and total records?") == QueryIntent.DATA_QUERY
    assert router.classify("Show me top non-compliant brands in inspection stats") == QueryIntent.DATA_QUERY

    # Hybrid Queries
    assert router.classify("What are the MRP rules and what is the violation rate in our scans?") == QueryIntent.HYBRID
    assert router.classify("How many scans failed net quantity rule?") == QueryIntent.HYBRID

    # Out-of-scope / Unknown Queries
    assert router.classify("How to bake a chocolate cake?") == QueryIntent.UNKNOWN
    assert router.classify("Who won the 2026 cricket world cup?") == QueryIntent.UNKNOWN


# 2. Test Rule Lookup with Official Citations and Source PDFs
def test_chatbot_rule_lookup_citations(in_memory_db):
    service = GroundedChatbotService()

    # MRP rule query
    res = service.process_query("What are the mandatory requirements for MRP declaration?", db=in_memory_db)
    assert res.intent in (QueryIntent.RULE_LOOKUP, QueryIntent.HYBRID)
    assert len(res.citations) > 0
    assert any("6(1)(e)" in c.official_legal_reference or c.rule_id == "LMPC_RULE_6_1_E" for c in res.citations)
    assert any(c.source_pdf for c in res.citations)
    assert "Rule 6(1)(e)" in res.reply or "MRP" in res.reply

    # Edible Oil SOP query
    res_oil = service.process_query("What is the SOP for edible oil and fats net quantity measurement?", db=in_memory_db)
    assert len(res_oil.citations) > 0
    assert any("Edible oil" in (c.source_pdf or "") or "SOP" in (c.official_legal_reference or "") or "6_1_C" in (c.rule_id or "") for c in res_oil.citations)


# 3. Test Hindi Query Retrieval and Devanagari Snippets
def test_chatbot_hindi_query(in_memory_db):
    service = GroundedChatbotService()

    res_hindi = service.process_query("शुद्ध मात्रा घोषणा नियम क्या है?", db=in_memory_db)
    assert res_hindi.intent == QueryIntent.RULE_LOOKUP
    assert len(res_hindi.citations) > 0
    # Must contain Hindi characters in reply or citation
    assert any('\u0900' <= c <= '\u097F' for c in res_hindi.reply)


# 4. Test Data Query Answering from Repository Metrics
def test_chatbot_data_query(in_memory_db):
    service = GroundedChatbotService()

    # Seed 2 scans in DB
    ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result={"overall_status": "COMPLIANT", "compliance_score": 100.0, "results": []},
        product_name="Brand A Flour",
        overall_status="COMPLIANT",
        compliance_score=100.0
    )
    ScanRepository.save_scan(
        db=in_memory_db,
        compliance_result={"overall_status": "NON_COMPLIANT", "compliance_score": 40.0, "results": []},
        product_name="Brand B Juice",
        overall_status="NON_COMPLIANT",
        compliance_score=40.0
    )

    res_data = service.process_query("How many total scans and what is the compliance rate?", db=in_memory_db)
    assert res_data.intent == QueryIntent.DATA_QUERY
    assert "2" in res_data.reply  # 2 total scans
    assert "50.0%" in res_data.reply  # 1 compliant out of 2 = 50%
    assert res_data.data_summary is not None
    assert res_data.data_summary["total_scans"] == 2


# 5. Test Strict Refusal for Out-of-Scope Hallucination Prevention
def test_chatbot_strict_refusal_for_out_of_scope(in_memory_db):
    service = GroundedChatbotService()

    out_of_scope_queries = [
        "What is the best recipe for Italian pasta?",
        "Who is the current prime minister of Australia?",
        "Write a Python script to sort a list of numbers"
    ]

    for q in out_of_scope_queries:
        res = service.process_query(q, db=in_memory_db)
        assert res.reply == STANDARD_REFUSAL_MESSAGE
        assert len(res.citations) == 0
        assert res.confidence == 0.0


# 6. Test FastAPI Authenticated POST /api/chat Endpoint
def test_api_chat_endpoint(in_memory_db):
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Register test officer
    hashed = get_password_hash("SecretChatbot123")
    officer = Officer(username="chatbot_inspector", hashed_password=hashed, role="inspector", is_active=True)
    in_memory_db.add(officer)
    in_memory_db.commit()

    token = create_access_token({"sub": "chatbot_inspector", "officer_id": officer.id, "role": "inspector"})
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # 1. Unauthenticated request -> 401 Unauthorized
        unauth_resp = client.post("/api/chat", json={"message": "What is Rule 6(1)(a)?"})
        assert unauth_resp.status_code == 401

        # 2. Authenticated request -> 200 OK with valid response schema
        auth_resp = client.post("/api/chat", json={"message": "What is Rule 6(1)(a)?"}, headers=headers)
        assert auth_resp.status_code == 200
        data = auth_resp.json()
        assert data["intent"] in ["RULE_LOOKUP", "HYBRID"]
        assert "Manufacturer" in data["reply"] or "Rule 6(1)(a)" in data["reply"]
        assert len(data["citations"]) > 0

        # 3. Authenticated out-of-scope query -> 200 OK with refusal reply
        refusal_resp = client.post("/api/chat", json={"message": "How to make coffee?"}, headers=headers)
        assert refusal_resp.status_code == 200
        assert "I don't have that information" in refusal_resp.json()["reply"]
    finally:
        app.dependency_overrides.clear()
