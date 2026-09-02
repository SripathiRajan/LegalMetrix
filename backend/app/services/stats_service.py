import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Union
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models import ScanRecord
from app.vision.readability import ReadabilityConfig
from app.rules.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class StatsService:
    """
    Service generating comprehensive Legal Metrology analytics, violation breakdowns,
    trend analysis, brand compliance rankings, authenticity flag rates, and font readability metrics.
    """

    def __init__(self, readability_config: Optional[ReadabilityConfig] = None):
        self.readability_config = readability_config or ReadabilityConfig()

    @staticmethod
    def _parse_date(date_val: Optional[Union[datetime, date, str]]) -> Optional[datetime]:
        """Parses various date formats into datetime object."""
        if date_val is None:
            return None
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, date):
            return datetime.combine(date_val, datetime.min.time())
        if isinstance(date_val, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
            except ValueError:
                try:
                    return datetime.strptime(date_val, "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Unable to parse date string: {date_val}")
                    return None
        return None

    def get_dashboard_statistics(
        self,
        db: Session,
        start_date: Optional[Union[datetime, str]] = None,
        end_date: Optional[Union[datetime, str]] = None
    ) -> Dict[str, Any]:
        """
        Computes the complete compliance dashboard analytics across persistent scan records.
        """
        dt_start = self._parse_date(start_date)
        dt_end = self._parse_date(end_date)

        query = db.query(ScanRecord)
        if dt_start:
            query = query.filter(ScanRecord.created_at >= dt_start)
        if dt_end:
            query = query.filter(ScanRecord.created_at <= dt_end)

        scans = query.order_by(ScanRecord.created_at.asc()).all()
        total_scans = len(scans)

        # 1. High-Level Summary
        compliant_count = sum(1 for s in scans if s.overall_status == "COMPLIANT")
        non_compliant_count = sum(
            1 for s in scans
            if s.overall_status in ("NON_COMPLIANT", "POTENTIALLY_NON_COMPLIANT")
        )
        avg_score = (
            round(sum(s.compliance_score for s in scans) / total_scans, 2)
            if total_scans > 0 else 0.0
        )
        compliance_rate = (
            round((compliant_count / total_scans) * 100.0, 2)
            if total_scans > 0 else 0.0
        )

        summary = {
            "total_scans": total_scans,
            "compliant_scans": compliant_count,
            "non_compliant_scans": non_compliant_count,
            "compliance_rate": compliance_rate,
            "average_compliance_score": avg_score
        }

        # 2. Violation Rate by Field (Enriched Rule IDs)
        field_evaluations = defaultdict(lambda: {"total": 0, "violations": 0, "declaration": "", "rule_id": ""})

        # Pre-seed with known standard rule IDs
        rule_map = RuleEngine.RULE_EVIDENCE_MAP
        for r_id, field_name in rule_map.items():
            field_evaluations[field_name]["rule_id"] = r_id
            field_evaluations[field_name]["declaration"] = field_name.replace("_", " ").title()

        for s in scans:
            comp_res = s.compliance_result or {}
            results_list = comp_res.get("results", [])
            for r in results_list:
                rule_id = r.get("rule_id", "")
                field_name = rule_map.get(rule_id, rule_id.lower())
                declaration = r.get("declaration", field_name)
                status_val = r.get("status", "")

                field_evaluations[field_name]["rule_id"] = rule_id
                field_evaluations[field_name]["declaration"] = declaration.split("(")[0].strip()
                field_evaluations[field_name]["total"] += 1

                if status_val in ("FAIL", "WARNING"):
                    field_evaluations[field_name]["violations"] += 1

        violation_rate_by_field = []
        for field_name, stats in field_evaluations.items():
            tot = stats["total"]
            viols = stats["violations"]
            v_rate = round((viols / tot) * 100.0, 2) if tot > 0 else 0.0
            violation_rate_by_field.append({
                "field_name": field_name,
                "rule_id": stats["rule_id"],
                "declaration_name": stats["declaration"],
                "total_evaluations": tot,
                "violation_count": viols,
                "violation_rate": v_rate
            })

        violation_rate_by_field.sort(key=lambda x: (x["violation_count"], x["violation_rate"]), reverse=True)

        # 3. Violation Trend Over Time (Daily Grouping)
        daily_buckets = defaultdict(lambda: {"total_scans": 0, "compliant_scans": 0, "violations_count": 0, "score_sum": 0.0})

        for s in scans:
            day_str = s.created_at.strftime("%Y-%m-%d") if s.created_at else "Unknown"
            daily_buckets[day_str]["total_scans"] += 1
            daily_buckets[day_str]["score_sum"] += s.compliance_score
            if s.overall_status == "COMPLIANT":
                daily_buckets[day_str]["compliant_scans"] += 1
            else:
                daily_buckets[day_str]["violations_count"] += 1

        violation_trend_over_time = []
        for day_str in sorted(daily_buckets.keys()):
            d_data = daily_buckets[day_str]
            d_total = d_data["total_scans"]
            d_comp_rate = round((d_data["compliant_scans"] / d_total) * 100.0, 2) if d_total > 0 else 0.0
            d_avg_score = round(d_data["score_sum"] / d_total, 2) if d_total > 0 else 0.0

            violation_trend_over_time.append({
                "date": day_str,
                "total_scans": d_total,
                "compliant_scans": d_data["compliant_scans"],
                "non_compliant_scans": d_data["violations_count"],
                "compliance_rate": d_comp_rate,
                "average_score": d_avg_score
            })

        # 4. Top Non-Compliant Brands
        brand_stats = defaultdict(lambda: {"total_scans": 0, "non_compliant_scans": 0, "score_sum": 0.0, "violations": defaultdict(int)})

        for s in scans:
            brand = s.product_name or "Unlabeled Commodity"
            brand_stats[brand]["total_scans"] += 1
            brand_stats[brand]["score_sum"] += s.compliance_score
            if s.overall_status != "COMPLIANT":
                brand_stats[brand]["non_compliant_scans"] += 1

            # Track violation types for this brand
            comp_res = s.compliance_result or {}
            for r in comp_res.get("results", []):
                if r.get("status") in ("FAIL", "WARNING"):
                    decl = r.get("declaration", "Unknown Declaration").split("(")[0].strip()
                    brand_stats[brand]["violations"][decl] += 1

        top_non_compliant_brands = []
        for brand, b_info in brand_stats.items():
            b_total = b_info["total_scans"]
            b_non_comp = b_info["non_compliant_scans"]
            b_avg_score = round(b_info["score_sum"] / b_total, 2) if b_total > 0 else 0.0

            # Most common violation
            if b_info["violations"]:
                most_common = max(b_info["violations"].items(), key=lambda x: x[1])[0]
            else:
                most_common = "None"

            top_non_compliant_brands.append({
                "brand_name": brand,
                "total_scans": b_total,
                "non_compliant_scans": b_non_comp,
                "non_compliance_rate": round((b_non_comp / b_total) * 100.0, 2) if b_total > 0 else 0.0,
                "average_compliance_score": b_avg_score,
                "most_common_violation": most_common
            })

        top_non_compliant_brands.sort(key=lambda x: (x["non_compliant_scans"], -x["average_compliance_score"]), reverse=True)
        top_non_compliant_brands = top_non_compliant_brands[:10]

        # 5. Authenticity Flag Rate
        auth_total = 0
        genuine_cnt = 0
        suspicious_cnt = 0
        no_ref_cnt = 0
        sim_scores = []

        for s in scans:
            auth_data = s.authenticity_result
            if auth_data:
                auth_total += 1
                verdict = auth_data.get("verdict", "")
                sim = auth_data.get("similarity_score")
                if sim is not None:
                    sim_scores.append(float(sim))

                if verdict == "GENUINE_LIKELY":
                    genuine_cnt += 1
                elif verdict == "SUSPICIOUS":
                    suspicious_cnt += 1
                elif verdict == "NO_REFERENCE_AVAILABLE":
                    no_ref_cnt += 1

        suspicious_rate = round((suspicious_cnt / auth_total) * 100.0, 2) if auth_total > 0 else 0.0
        avg_sim = round(sum(sim_scores) / len(sim_scores), 4) if sim_scores else 0.0

        authenticity_flag_rate = {
            "total_scans_evaluated": auth_total,
            "genuine_count": genuine_cnt,
            "suspicious_count": suspicious_cnt,
            "no_reference_count": no_ref_cnt,
            "suspicious_flag_rate": suspicious_rate,
            "average_similarity_score": avg_sim
        }

        # 6. Font Size Distribution (Reusing ReadabilityConfig Constants)
        warn_px = self.readability_config.warning_text_height_pixels  # 8.0px
        min_px = self.readability_config.minimum_text_height_pixels    # 12.0px
        std_px = 24.0

        font_buckets = {
            "under_8px": 0,
            "between_8_12px": 0,
            "between_12_24px": 0,
            "over_24px": 0
        }
        text_heights: List[float] = []

        for s in scans:
            # Check results evidence
            comp_res = s.compliance_result or {}
            for r in comp_res.get("results", []):
                ev = r.get("evidence")
                if ev and isinstance(ev, dict):
                    h_px = ev.get("pixel_text_height") or ev.get("text_height_pixels")
                    if h_px is not None:
                        h_val = float(h_px)
                        text_heights.append(h_val)
                        if h_val < warn_px:
                            font_buckets["under_8px"] += 1
                        elif h_val < min_px:
                            font_buckets["between_8_12px"] += 1
                        elif h_val < std_px:
                            font_buckets["between_12_24px"] += 1
                        else:
                            font_buckets["over_24px"] += 1

            # Check extracted data evidence if results had none
            ext_data = s.extracted_data or {}
            if not text_heights and isinstance(ext_data, dict):
                for field_val in ext_data.values():
                    if isinstance(field_val, dict):
                        ev = field_val.get("evidence")
                        if ev and isinstance(ev, dict):
                            h_px = ev.get("pixel_text_height")
                            if h_px is not None:
                                h_val = float(h_px)
                                text_heights.append(h_val)
                                if h_val < warn_px:
                                    font_buckets["under_8px"] += 1
                                elif h_val < min_px:
                                    font_buckets["between_8_12px"] += 1
                                elif h_val < std_px:
                                    font_buckets["between_12_24px"] += 1
                                else:
                                    font_buckets["over_24px"] += 1

        total_font_regions = len(text_heights)
        avg_font_height = round(sum(text_heights) / total_font_regions, 1) if total_font_regions > 0 else 0.0
        below_min_rate = (
            round(((font_buckets["under_8px"] + font_buckets["between_8_12px"]) / total_font_regions) * 100.0, 2)
            if total_font_regions > 0 else 0.0
        )

        font_size_distribution = {
            "thresholds": {
                "warning_threshold_px": warn_px,
                "minimum_threshold_px": min_px,
                "standard_threshold_px": std_px
            },
            "distribution": font_buckets,
            "total_regions_evaluated": total_font_regions,
            "average_text_height_px": avg_font_height,
            "percentage_below_minimum": below_min_rate
        }

        return {
            "summary": summary,
            "violation_rate_by_field": violation_rate_by_field,
            "violation_trend_over_time": violation_trend_over_time,
            "top_non_compliant_brands": top_non_compliant_brands,
            "authenticity_flag_rate": authenticity_flag_rate,
            "font_size_distribution": font_size_distribution
        }
