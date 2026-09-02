from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class OfficerRegister(BaseModel):
    """Payload for registering a new Inspector / Officer account."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: Optional[str] = Field(None, description="Official email address")
    password: str = Field(..., min_length=6, description="Account password")
    badge_number: Optional[str] = Field(None, description="Department Inspector Badge Number")
    role: str = Field("inspector", description="Role: 'inspector' or 'admin'")


class OfficerLogin(BaseModel):
    """Payload for officer login credentials."""
    username: str = Field(..., description="Registered username")
    password: str = Field(..., description="Account password")


class OfficerProfile(BaseModel):
    """Public profile of an authenticated Officer."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: Optional[str] = None
    badge_number: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime] = None


class Token(BaseModel):
    """JWT Token response format."""
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    officer: OfficerProfile


class TokenPayload(BaseModel):
    """Decoded JWT payload data."""
    sub: str  # username
    officer_id: Optional[int] = None
    role: Optional[str] = "inspector"
    exp: Optional[int] = None


class ChatbotQueryRequest(BaseModel):
    """Request payload for semantic Legal Metrology chatbot queries."""
    query: str = Field(..., min_length=2, description="Legal question or commodity declaration query")
    top_k: int = Field(3, ge=1, le=10, description="Number of relevant DoCA citations to retrieve")


class ChatbotQueryResponse(BaseModel):
    """Response containing retrieved DoCA legal citations and grounded answers."""
    query: str
    results_count: int
    citations: List[Dict[str, Any]]
