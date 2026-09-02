from typing import Optional
from app.models.product import ProductInput, RuleDefinition, RuleCheckResult, RuleStatus, SeverityLevel
from app.validators.base import BaseValidator


class OriginValidator(BaseValidator):
    """
    Validator for Country of Origin on imported commodities per Rule 6(1)(da)
    of Legal Metrology (Packaged Commodities) Rules, 2011.
    """

    KNOWN_COUNTRIES = [
        "india", "china", "vietnam", "thailand", "indonesia", "usa", "united states",
        "united kingdom", "uk", "germany", "japan", "south korea", "korea", "france",
        "italy", "malaysia", "taiwan", "bangladesh", "sri lanka", "spain", "brazil",
        "mexico", "australia", "canada", "singapore", "uae", "switzerland", "netherlands"
    ]

    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        origin = product.country_of_origin
        is_imported = product.is_imported or (origin and origin.strip().lower() not in ["india", "in", "ind"])

        # If product is purely domestic and no origin was declared
        if not is_imported and (origin is None or not str(origin).strip()):
            return self.create_result(
                rule=rule,
                status=RuleStatus.NOT_APPLICABLE,
                detected_value=None,
                reason="Country of origin declaration is specifically mandatory for imported packages under Rule 6(1)(da). Not applicable for domestic goods with complete manufacturer address.",
                severity=SeverityLevel.LOW
            )

        if origin is None or not str(origin).strip():
            # Product is flagged as imported, but origin is missing
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=None,
                reason="Product is marked as imported, but Country of Origin is missing. Mandatory under Rule 6(1)(da).",
                severity=SeverityLevel.HIGH
            )

        origin_str = str(origin).strip()
        origin_lower = origin_str.lower()

        if any(c in origin_lower for c in self.KNOWN_COUNTRIES) or len(origin_str) >= 2:
            return self.create_result(
                rule=rule,
                status=RuleStatus.PASS,
                detected_value=origin_str,
                reason=f"Country of Origin '{origin_str}' clearly declared per Rule 6(1)(da).",
                severity=SeverityLevel.HIGH,
                metadata={"country": origin_str, "is_imported": is_imported}
            )

        return self.create_result(
            rule=rule,
            status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
            detected_value=origin_str,
            reason=f"Country of origin value '{origin_str}' could not be verified automatically. Requires manual verification.",
            severity=SeverityLevel.MEDIUM
        )
