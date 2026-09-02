from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    RULE_LOOKUP = "RULE_LOOKUP"
    DATA_QUERY = "DATA_QUERY"
    HYBRID = "HYBRID"
    UNKNOWN = "UNKNOWN"


class ChatRequest(BaseModel):
    """User prompt sent to the Grounded Legal Metrology Chatbot."""
    message: str = Field(..., min_length=1, description="User question or query")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional conversation state or product context")


class Citation(BaseModel):
    """Official citation metadata grounded in the DoCA dataset."""
    rule_id: Optional[str] = None
    declaration_name: str
    official_legal_reference: str
    source_pdf: Optional[str] = None
    english_text: Optional[str] = None
    hindi_text_snippet: Optional[str] = None
    last_amended_date: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    """Grounded chatbot response with official citations or empirical database metrics."""
    query: str
    intent: QueryIntent
    reply: str
    citations: List[Citation] = Field(default_factory=list)
    data_summary: Optional[Dict[str, Any]] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
