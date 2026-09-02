import re
from typing import Optional
from app.models.product import ProductInput, RuleDefinition, RuleCheckResult, RuleStatus, SeverityLevel
from app.validators.base import BaseValidator


from app.extraction.normalizer import FieldNormalizer


class CommodityNameValidator(BaseValidator):
    """
    Validator for Generic / Common Name of Commodity per Rule 6(1)(b)
    of Legal Metrology (Packaged Commodities) Rules, 2011.
    """

    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        name = product.generic_name or product.product_name

        if name is None or not str(name).strip():
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=None,
                reason="Generic or common name of commodity is missing. Mandatory under Rule 6(1)(b).",
                severity=SeverityLevel.MEDIUM
            )

        name_str = str(name).strip()

        # Reject pure product/batch codes (e.g. S60017, AB1234, 98765)
        if FieldNormalizer.is_code_like(name_str):
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=name_str,
                reason=f"Detected value '{name_str}' appears to be a product/batch code, not a common/generic commodity name as required under Rule 6(1)(b).",
                severity=SeverityLevel.HIGH
            )

        if len(name_str) < 2:
            return self.create_result(
                rule=rule,
                status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
                detected_value=name_str,
                reason=f"Detected product name '{name_str}' is extremely short and may be an OCR fragment.",
                severity=SeverityLevel.MEDIUM
            )

        return self.create_result(
            rule=rule,
            status=RuleStatus.PASS,
            detected_value=name_str,
            reason=f"Common/generic commodity name '{name_str}' declared per Rule 6(1)(b).",
            severity=SeverityLevel.MEDIUM
        )



class UnitSalePriceValidator(BaseValidator):
    """
    Validator for Unit Sale Price (USP) per Rule 6(1)(e)(ii) & (iii) (as amended).
    """

    USP_PATTERN = re.compile(r'(?:₹|Rs\.?|INR)?\s*([0-9]+(?:\.[0-9]{1,2})?)\s*(?:/|per)\s*([a-zA-Z]+)', re.IGNORECASE)

    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        usp = product.unit_sale_price

        if usp is None or not str(usp).strip():
            # If not explicitly provided, check if mandatory
            if product.package_type == "multi_unit":
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.WARNING,
                    detected_value=None,
                    reason="Unit Sale Price is recommended for multi-unit packages under amended Rule 6(1)(e).",
                    severity=SeverityLevel.LOW
                )
            return self.create_result(
                rule=rule,
                status=RuleStatus.NOT_APPLICABLE,
                detected_value=None,
                reason="Unit Sale Price not declared (conditional on package category / volume).",
                severity=SeverityLevel.LOW
            )

        usp_str = str(usp).strip()
        match = self.USP_PATTERN.search(usp_str)

        if match:
            return self.create_result(
                rule=rule,
                status=RuleStatus.PASS,
                detected_value=usp_str,
                reason=f"Valid Unit Sale Price '{usp_str}' declared in standard per-unit format.",
                severity=SeverityLevel.LOW
            )

        return self.create_result(
            rule=rule,
            status=RuleStatus.WARNING,
            detected_value=usp_str,
            reason=f"Unit Sale Price '{usp_str}' does not strictly follow '₹ X.XX / unit' standard notation.",
            severity=SeverityLevel.LOW
        )
