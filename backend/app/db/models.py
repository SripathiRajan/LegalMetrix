from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Text
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Officer(Base):
    """
    Inspector / Officer user model for authentication and scan audit attribution.
    """
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    badge_number = Column(String(100), nullable=True, index=True)
    role = Column(String(50), default="inspector", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    scans = relationship("ScanRecord", back_populates="officer")


class ScanRecord(Base):
    """
    Persistent audit scan record storing complete Legal Metrology assessment,
    extracted product declarations, authenticity results, and visual evidence.
    """
    __tablename__ = "scan_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_name = Column(String(255), nullable=True, index=True)
    overall_status = Column(String(50), nullable=False, index=True)
    compliance_score = Column(Float, nullable=False, default=0.0)
    
    # JSON payloads preserving exact Pydantic schema structures
    compliance_result = Column(JSON, nullable=False)
    authenticity_result = Column(JSON, nullable=True)
    visual_statistics = Column(JSON, nullable=True)
    extracted_data = Column(JSON, nullable=True)

    image_path = Column(String(500), nullable=True)
    officer_id = Column(Integer, ForeignKey("officers.id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    officer = relationship("Officer", back_populates="scans")
