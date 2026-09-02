import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import ScanRecord
from app.db.scan_repository import ScanRepository
from app.models.product import ComplianceResponse
from app.models.extracted_product import ExtractedProductData, AuthenticityResult

logger = logging.getLogger(__name__)


class HistoryService:
    """
    Application Service for scan persistence, inspection audit logs,
    and historical compliance trend reporting.
    """

    def __init__(self, repository: Optional[ScanRepository] = None):
        self.repository = repository or ScanRepository()

    def record_scan(
        self,
        compliance_result: Any,
        extracted_data: Optional[Any] = None,
        authenticity_result: Optional[Any] = None,
        visual_statistics: Optional[Dict[str, Any]] = None,
        image_path: Optional[str] = None,
        officer_id: Optional[int] = None,
        db: Optional[Session] = None
    ) -> ScanRecord:
        """
        Serializes assessment domain objects and persists a new ScanRecord.
        """
        # Convert Pydantic objects to dicts if needed
        comp_dict = (
            compliance_result.model_dump()
            if hasattr(compliance_result, "model_dump")
            else dict(compliance_result)
        )
        ext_dict = (
            extracted_data.model_dump()
            if hasattr(extracted_data, "model_dump")
            else (dict(extracted_data) if extracted_data else None)
        )
        auth_dict = (
            authenticity_result.model_dump()
            if hasattr(authenticity_result, "model_dump")
            else (dict(authenticity_result) if authenticity_result else None)
        )

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            record = self.repository.save_scan(
                db=db,
                compliance_result=comp_dict,
                extracted_data=ext_dict,
                authenticity_result=auth_dict,
                visual_statistics=visual_statistics,
                image_path=image_path,
                officer_id=officer_id
            )
            return record
        finally:
            if close_session:
                db.close()

    def get_scan_by_id(
        self,
        scan_id: int,
        db: Optional[Session] = None
    ) -> Optional[ScanRecord]:
        """
        Fetches an individual scan record by ID.
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            return self.repository.get_scan(db=db, scan_id=scan_id)
        finally:
            if close_session:
                db.close()

    def list_scans(
        self,
        status: Optional[str] = None,
        officer_id: Optional[int] = None,
        product_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Queries paginated scan history with filter criteria.
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            records, total = self.repository.list_scans(
                db=db,
                status=status,
                officer_id=officer_id,
                product_name=product_name,
                limit=limit,
                offset=offset
            )
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": [
                    {
                        "id": r.id,
                        "product_name": r.product_name,
                        "overall_status": r.overall_status,
                        "compliance_score": r.compliance_score,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "image_path": r.image_path,
                        "officer_id": r.officer_id,
                        "compliance_result": r.compliance_result,
                        "authenticity_result": r.authenticity_result,
                        "extracted_data": r.extracted_data,
                        "visual_statistics": r.visual_statistics
                    }
                    for r in records
                ]
            }
        finally:
            if close_session:
                db.close()

    def get_dashboard_metrics(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Retrieves high-level compliance dashboard metrics.
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            return self.repository.get_compliance_aggregates(db=db)
        finally:
            if close_session:
                db.close()
