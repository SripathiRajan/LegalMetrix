import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.models import ScanRecord, Officer

logger = logging.getLogger(__name__)


class ScanRepository:
    """
    Data Access Repository for managing persistent scan records, filtering,
    pagination, and aggregate compliance analytics.
    """

    @staticmethod
    def save_scan(
        db: Session,
        compliance_result: Dict[str, Any],
        extracted_data: Optional[Dict[str, Any]] = None,
        authenticity_result: Optional[Dict[str, Any]] = None,
        visual_statistics: Optional[Dict[str, Any]] = None,
        image_path: Optional[str] = None,
        officer_id: Optional[int] = None,
        product_name: Optional[str] = None,
        overall_status: Optional[str] = None,
        compliance_score: Optional[float] = None
    ) -> ScanRecord:
        """
        Creates and persists a new ScanRecord entry.
        """
        # Infer values if not explicitly provided
        if overall_status is None:
            overall_status = compliance_result.get("overall_status", "UNKNOWN")

        if hasattr(overall_status, "value"):
            overall_status_str = str(overall_status.value)
        elif isinstance(overall_status, str):
            overall_status_str = overall_status.split(".")[-1] if "." in overall_status else overall_status
        else:
            overall_status_str = str(overall_status)

        if compliance_score is None:
            compliance_score = float(compliance_result.get("compliance_score", 0.0))
        if product_name is None and extracted_data:
            prod_field = extracted_data.get("product_name", {})
            product_name = prod_field.get("value") if isinstance(prod_field, dict) else None

        record = ScanRecord(
            product_name=product_name,
            overall_status=overall_status_str,
            compliance_score=round(float(compliance_score), 2),

            compliance_result=compliance_result,
            authenticity_result=authenticity_result,
            visual_statistics=visual_statistics,
            extracted_data=extracted_data,
            image_path=image_path,
            officer_id=officer_id
        )

        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Persisted scan record #{record.id} for product '{product_name}' status={overall_status}")
        return record

    @staticmethod
    def get_scan(db: Session, scan_id: int) -> Optional[ScanRecord]:
        """
        Retrieves a single scan record by ID.
        """
        return db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()

    @staticmethod
    def list_scans(
        db: Session,
        status: Optional[str] = None,
        officer_id: Optional[int] = None,
        product_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ScanRecord], int]:
        """
        Queries scan records with optional filters, ordering descending by creation date with pagination.
        Returns (records, total_count).
        """
        query = db.query(ScanRecord)

        if status:
            query = query.filter(ScanRecord.overall_status == status.upper())
        if officer_id:
            query = query.filter(ScanRecord.officer_id == officer_id)
        if product_name:
            query = query.filter(ScanRecord.product_name.ilike(f"%{product_name}%"))
        if date_from:
            query = query.filter(ScanRecord.created_at >= date_from)
        if date_to:
            query = query.filter(ScanRecord.created_at <= date_to)

        total_count = query.count()
        records = (
            query.order_by(desc(ScanRecord.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return records, total_count

    @staticmethod
    def get_compliance_aggregates(db: Session) -> Dict[str, Any]:
        """
        Calculates compliance dashboard metrics:
          - Total scans count
          - Status counts (COMPLIANT, NON_COMPLIANT, etc.)
          - Average compliance score
          - Compliance rate percentage
          - Authenticity breakdown
        """
        total_scans = db.query(ScanRecord).count()

        if total_scans == 0:
            return {
                "total_scans": 0,
                "compliant_count": 0,
                "non_compliant_count": 0,
                "compliance_rate": 0.0,
                "average_score": 0.0,
                "status_distribution": {},
                "authenticity_distribution": {}
            }

        # Status distribution
        status_counts = (
            db.query(ScanRecord.overall_status, func.count(ScanRecord.id))
            .group_by(ScanRecord.overall_status)
            .all()
        )
        status_dict = {str(status): count for status, count in status_counts}

        # Average compliance score
        avg_score = db.query(func.avg(ScanRecord.compliance_score)).scalar() or 0.0

        compliant_count = status_dict.get("COMPLIANT", 0)
        non_compliant_count = (
            status_dict.get("NON_COMPLIANT", 0)
            + status_dict.get("POTENTIALLY_NON_COMPLIANT", 0)
        )
        compliance_rate = round((compliant_count / total_scans) * 100.0, 2)

        return {
            "total_scans": total_scans,
            "compliant_count": compliant_count,
            "non_compliant_count": non_compliant_count,
            "compliance_rate": compliance_rate,
            "average_score": round(float(avg_score), 2),
            "status_distribution": status_dict
        }

    @staticmethod
    def delete_scan(db: Session, scan_id: int) -> bool:
        """Deletes a scan record by ID."""
        record = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
        if record:
            db.delete(record)
            db.commit()
            return True
        return False
