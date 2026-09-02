import re
from typing import Optional
from app.models.product import ProductInput, RuleDefinition, RuleCheckResult, RuleStatus, SeverityLevel
from app.validators.base import BaseValidator


class QuantityValidator(BaseValidator):
    """
    Validator for Net Quantity per Rule 6(1)(c) and Rules 11, 12, 13 & Second Schedule
    of Legal Metrology (Packaged Commodities) Rules, 2011.
    """

    # Permitted standard units of weight, measure, volume, length, area, number
    # Standard metric symbols per Rule 13:
    # Mass: g, kg, mg
    # Volume: ml, l, L, mL, c.c., cm3
    # Length: mm, cm, m
    # Area: sq cm, sq m, cm2, m2
    # Number: N, U, units, pieces, pcs, count, nos, no.
    # Non-standard/illegal: 'gms', 'gms.', 'kgs', 'kilo', 'kilos', 'litres', 'ltrs', 'ml.'
    
    STANDARD_UNITS = {
        "mass": ["g", "kg", "mg"],
        "volume": ["ml", "l", "cl", "cm3"],
        "length": ["mm", "cm", "m"],
        "area": ["sq cm", "sq m", "cm2", "m2"],
        "number": ["n", "u", "unit", "units", "pcs", "piece", "pieces", "count", "nos", "no"]
    }

    # Regex to extract quantity number and unit
    QUANTITY_REGEX = re.compile(
        r'^\s*(?:net\s*(?:qty|quantity|wt|weight)?\s*[:\-\.]?\s*)?([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*([a-zA-Z0-9\.\^²³]+(?:\s+[a-zA-Z0-9]+)?)\s*$',
        re.IGNORECASE
    )

    NON_STANDARD_UNITS = {
        "gms": "g",
        "gm": "g",
        "gms.": "g",
        "kgs": "kg",
        "kgs.": "kg",
        "kilo": "kg",
        "kilos": "kg",
        "ltr": "l",
        "ltrs": "l",
        "ltr.": "l",
        "litres": "l",
        "liter": "l",
        "liters": "l",
        "mls": "ml",
        "mls.": "ml",
        "mtr": "m",
        "mtrs": "m",
        "cnt": "N",
    }

    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        raw_quantity = product.net_quantity

        if raw_quantity is None or not str(raw_quantity).strip():
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=None,
                reason="Net quantity declaration is missing. Mandatory under Rule 6(1)(c).",
                severity=SeverityLevel.HIGH
            )

        qty_str = str(raw_quantity).strip()

        # Handle explicit numbers or standard string expressions
        match = self.QUANTITY_REGEX.match(qty_str)
        if not match:
            # Check if there is at least some number and unit buried in OCR string
            fallback_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)', qty_str)
            if not fallback_match:
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.FAIL,
                    detected_value=qty_str,
                    reason=f"Invalid net quantity format '{qty_str}'. Must include numerical value and standard unit.",
                    severity=SeverityLevel.HIGH
                )
            num_part = fallback_match.group(1)
            unit_part = fallback_match.group(2).strip().lower()
        else:
            num_part = match.group(1)
            unit_part = match.group(2).strip().lower()

        try:
            qty_num = float(num_part)
            if qty_num <= 0:
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.FAIL,
                    detected_value=qty_str,
                    reason=f"Net quantity value must be greater than zero. Found: {qty_num}",
                    severity=SeverityLevel.HIGH
                )
        except ValueError:
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=qty_str,
                reason=f"Numerical portion of net quantity '{num_part}' is invalid.",
                severity=SeverityLevel.HIGH
            )

        # Check for prohibited symbols per Rule 13 (e.g. 'gms', 'kgs', 'ltrs' are improper under Legal Metrology)
        cleaned_unit = unit_part.rstrip('.').lower()

        if cleaned_unit in self.NON_STANDARD_UNITS:
            corrected = self.NON_STANDARD_UNITS[cleaned_unit]
            return self.create_result(
                rule=rule,
                status=RuleStatus.WARNING,
                detected_value=qty_str,
                reason=f"Non-standard unit symbol '{unit_part}' used. Legal Metrology Rule 13 prescribes standard symbol '{corrected}' (not pluralized or non-metric symbols).",
                severity=SeverityLevel.MEDIUM,
                metadata={"parsed_quantity": qty_num, "unit": unit_part, "recommended_unit": corrected}
            )

        # Check if unit is in standard metric units
        all_standard_units = [u for sublist in self.STANDARD_UNITS.values() for u in sublist]
        if cleaned_unit in all_standard_units or unit_part.upper() in ["N", "U"]:
            return self.create_result(
                rule=rule,
                status=RuleStatus.PASS,
                detected_value=qty_str,
                reason=f"Valid net quantity declared ({qty_num} {unit_part}) in standard Legal Metrology units per Rule 6(1)(c) and Rule 13.",
                severity=SeverityLevel.HIGH,
                metadata={"parsed_quantity": qty_num, "unit": unit_part}
            )

        # Unknown or suspicious unit (e.g., non-metric, obscure abbreviations)
        return self.create_result(
            rule=rule,
            status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
            detected_value=qty_str,
            reason=f"Quantity '{qty_str}' contains unrecognized or non-standard measurement unit '{unit_part}'. Verification required against Second/Third Schedule.",
            severity=SeverityLevel.MEDIUM,
            metadata={"parsed_quantity": qty_num, "unit": unit_part}
        )
