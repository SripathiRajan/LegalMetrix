import re
from datetime import datetime
from typing import Optional
from app.models.product import ProductInput, RuleDefinition, RuleCheckResult, RuleStatus, SeverityLevel
from app.validators.base import BaseValidator


class DateValidator(BaseValidator):
    """
    Validator for Month and Year of Manufacture / Packing / Import
    per Rule 6(1)(d) and Best Before per Rule 6(1)(f) of
    Legal Metrology (Packaged Commodities) Rules, 2011.
    """

    MONTH_NAMES = [
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec",
        "january", "february", "march", "april", "june",
        "july", "august", "september", "october", "november", "december"
    ]

    # Patterns for valid month/year declarations:
    # MM/YYYY, MM/YY, MM-YYYY, MM-YY, Month YYYY, Month YY, DD/MM/YYYY, DD-MM-YYYY
    PATTERNS = [
        (re.compile(r'^(0?[1-9]|1[0-2])[/\-\.](20\d{2}|\d{2})$'), "MM/YYYY or MM/YY"),
        (re.compile(r'^(0?[1-9]|[12]\d|3[01])[/\-\.](0?[1-9]|1[0-2])[/\-\.](20\d{2}|\d{2})$'), "DD/MM/YYYY"),
        (re.compile(r'^(?:mfg|pkd|packed|mfd|imported)?\s*[:\-\.]?\s*([a-zA-Z]{3,9})\s*[/\-\.\s]\s*(20\d{2}|\d{2})$', re.IGNORECASE), "Month Year"),
        (re.compile(r'^(?:mfg|pkd|packed|mfd|imported)?\s*[:\-\.]?\s*(0?[1-9]|1[0-2])[/\-\.](20\d{2}|\d{2})$', re.IGNORECASE), "MM/YYYY with prefix")
    ]

    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        # Determine whether this is validating manufacturing date or best before date
        is_best_before = rule.field_name == "best_before_date"
        raw_date = product.best_before_date if is_best_before else product.date_declaration

        # If mandatory rule (like Rule 6(1)(d)) and value is missing
        if raw_date is None or not str(raw_date).strip():
            if rule.mandatory:
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.FAIL,
                    detected_value=None,
                    reason="Month and Year of manufacture / packing / import is missing. Mandatory under Rule 6(1)(d).",
                    severity=SeverityLevel.HIGH
                )
            else:
                # Conditional rule (e.g. best before for non-food)
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.NOT_APPLICABLE,
                    detected_value=None,
                    reason="Best before / Use by date not declared and not strictly required for this commodity.",
                    severity=SeverityLevel.LOW
                )

        date_str = str(raw_date).strip()

        # Check for relative statements (e.g., "Best before 6 months from packaging / mfg")
        if re.search(r'best\s*before\s*\d+\s*months?', date_str, re.IGNORECASE):
            return self.create_result(
                rule=rule,
                status=RuleStatus.PASS,
                detected_value=date_str,
                reason="Valid relative expiry duration declared per Rule 6(1)(f) ('Best before X months from manufacture').",
                severity=rule.severity,
                metadata={"type": "relative_duration"}
            )

        # Check for ambiguous text or single digits
        if len(date_str) < 4 and not re.match(r'^\d{2}/\d{2}$', date_str):
            return self.create_result(
                rule=rule,
                status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
                detected_value=date_str,
                reason=f"Ambiguous or partial date declaration '{date_str}'. Requires visual verification of packaging.",
                severity=SeverityLevel.MEDIUM
            )

        # Match patterns
        matched = False
        parsed_format = ""
        for pattern, fmt_name in self.PATTERNS:
            match = pattern.match(date_str)
            if match:
                matched = True
                parsed_format = fmt_name
                break

        if not matched:
            # Check if any month name is in the string
            tokens = [t.lower() for t in re.split(r'[\s/\-\.,]+', date_str) if t]
            has_month = any(t in self.MONTH_NAMES for t in tokens)
            has_year = any(re.match(r'^(20\d{2}|\d{2})$', t) for t in tokens)
            
            if has_month and has_year:
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.PASS,
                    detected_value=date_str,
                    reason=f"Valid date declaration '{date_str}' containing recognized month and year per Rule 6(1)(d).",
                    severity=rule.severity,
                    metadata={"parsed_format": "Natural Month Year"}
                )

            # Check if date contains purely numeric ambiguous values
            if re.search(r'\d+', date_str):
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
                    detected_value=date_str,
                    reason=f"Date string '{date_str}' contains numbers but does not follow standard Month/Year format (MM/YYYY or Month YYYY). Human verification required.",
                    severity=SeverityLevel.MEDIUM
                )
            
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=date_str,
                reason=f"Unrecognized date declaration format '{date_str}'. Rule 6(1)(d) mandates month and year.",
                severity=SeverityLevel.HIGH
            )

        return self.create_result(
            rule=rule,
            status=RuleStatus.PASS,
            detected_value=date_str,
            reason=f"Valid month/year declaration '{date_str}' matching format {parsed_format} per Rule 6(1)(d).",
            severity=rule.severity,
            metadata={"parsed_format": parsed_format}
        )
