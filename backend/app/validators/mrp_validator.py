import re
from typing import Optional
from app.models.product import ProductInput, RuleDefinition, RuleCheckResult, RuleStatus, SeverityLevel
from app.validators.base import BaseValidator


class MRPValidator(BaseValidator):
    """
    Validator for Maximum Retail Price (MRP) per Rule 6(1)(e) and Rule 2(m)
    of Legal Metrology (Packaged Commodities) Rules, 2011.
    """

    # Matches ₹, Rs., Rs, INR followed by valid positive numbers (e.g., 50, 50.00, 1,200.50)
    MRP_NUMERIC_PATTERN = re.compile(
        r'(?:₹|Rs\.?|INR)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)',
        re.IGNORECASE
    )

    INCL_TAXES_PATTERN = re.compile(
        r'(?:incl(?:\.|usive)?\s*(?:of)?\s*all\s*taxes|incl\.?\s*taxes)',
        re.IGNORECASE
    )

    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        raw_mrp = product.mrp

        # If missing completely
        if raw_mrp is None or not str(raw_mrp).strip():
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=None,
                reason="Maximum Retail Price (MRP) declaration is missing. Mandatory under Rule 6(1)(e).",
                severity=SeverityLevel.HIGH
            )

        mrp_str = str(raw_mrp).strip()

        # Check for non-numeric/corrupted OCR or placeholder strings
        if mrp_str.lower() in ["na", "null", "none", "0", "₹0", "rs.0", "rs 0", "free"]:
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=mrp_str,
                reason=f"Invalid MRP value '{mrp_str}'. Packaged retail commodities must declare a valid positive price.",
                severity=SeverityLevel.HIGH
            )

        # Check numeric format
        match = self.MRP_NUMERIC_PATTERN.search(mrp_str)
        if not match:
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=mrp_str,
                reason=f"MRP '{mrp_str}' could not be parsed into a valid currency denomination format.",
                severity=SeverityLevel.HIGH
            )

        extracted_number_str = match.group(1).replace(",", "")
        try:
            numeric_val = float(extracted_number_str)
            if numeric_val <= 0:
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.FAIL,
                    detected_value=mrp_str,
                    reason=f"MRP value must be greater than zero. Detected: {numeric_val}",
                    severity=SeverityLevel.HIGH
                )
        except ValueError:
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=mrp_str,
                reason=f"MRP '{mrp_str}' contains an invalid numerical value.",
                severity=SeverityLevel.HIGH
            )

        # Check if currency symbol or identifier is present
        has_currency_indicator = bool(re.search(r'(₹|Rs\.?|INR)', mrp_str, re.IGNORECASE))
        has_incl_taxes = bool(self.INCL_TAXES_PATTERN.search(mrp_str))

        # Full compliance with standard Indian retail format
        if has_currency_indicator and has_incl_taxes:
            return self.create_result(
                rule=rule,
                status=RuleStatus.PASS,
                detected_value=mrp_str,
                reason="Valid MRP declared with currency symbol and 'inclusive of all taxes' per Rule 6(1)(e).",
                severity=SeverityLevel.HIGH,
                metadata={"parsed_amount": numeric_val, "has_currency_indicator": True, "has_incl_taxes": True}
            )
        elif has_currency_indicator or numeric_val > 0:
            # Price is clearly present, but missing 'incl. of all taxes' or formal prefix
            warning_reasons = []
            if not has_currency_indicator:
                warning_reasons.append("Currency symbol (₹ / Rs.) is missing")
            if not has_incl_taxes:
                warning_reasons.append("'inclusive of all taxes' declaration phrase is missing or truncated in OCR")

            return self.create_result(
                rule=rule,
                status=RuleStatus.WARNING,
                detected_value=mrp_str,
                reason=f"MRP value ₹{numeric_val:.2f} detected, but with format irregularity: {'; '.join(warning_reasons)}. Rule 6(1)(e) requires 'inclusive of all taxes'.",
                severity=SeverityLevel.MEDIUM,
                metadata={"parsed_amount": numeric_val, "has_currency_indicator": has_currency_indicator, "has_incl_taxes": has_incl_taxes}
            )

        return self.create_result(
            rule=rule,
            status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
            detected_value=mrp_str,
            reason="MRP string detected but contains ambiguous characters requiring human verification.",
            severity=SeverityLevel.HIGH
        )
