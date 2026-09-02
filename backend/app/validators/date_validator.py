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
    # Tuple format: (pattern_regex, format_name, year_group_index, month_group_index_or_none)
    PATTERNS = [
        (re.compile(r'^(0?[1-9]|1[0-2])[/\-\.](\d{4}|\d{2})$'), "MM/YYYY or MM/YY", 2, None),
        (re.compile(r'^(0?[1-9]|[12]\d|3[01])[/\-\.](0?[1-9]|1[0-2])[/\-\.](\d{4}|\d{2})$'), "DD/MM/YYYY", 3, None),
        (re.compile(r'^(?:mfg|pkd|packed|mfd|imported)?\s*[:\-\.]?\s*([a-zA-Z]{3,9})\s*[/\-\.\s]\s*(\d{4}|\d{2})$', re.IGNORECASE), "Month Year", 2, 1),
        (re.compile(r'^(?:mfg|pkd|packed|mfd|imported)?\s*[:\-\.]?\s*(0?[1-9]|1[0-2])[/\-\.](\d{4}|\d{2})$', re.IGNORECASE), "MM/YYYY with prefix", 2, None)
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
        year_str: Optional[str] = None

        for item in self.PATTERNS:
            pattern, fmt_name, yr_idx, mo_idx = item
            match = pattern.match(date_str)
            if match:
                if mo_idx is not None and match.group(mo_idx).lower() not in self.MONTH_NAMES:
                    continue
                matched = True
                parsed_format = fmt_name
                year_str = match.group(yr_idx)
                break

        if not matched:
            # Check if any month name is in the string
            tokens = [t.lower() for t in re.split(r'[\s/\-\.,]+', date_str) if t]
            has_month = any(t in self.MONTH_NAMES for t in tokens)
            year_token = next((t for t in tokens if re.match(r'^(\d{4}|\d{2})$', t)), None)
            
            if has_month and year_token:
                matched = True
                parsed_format = "Natural Month Year"
                year_str = year_token

        if not matched:
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

        # Realistic year validation (between 2015 and current_year + 1)
        current_year = datetime.now().year
        max_year = current_year + 1
        min_year = 2015

        if year_str:
            if len(year_str) == 2:
                year_int = 2000 + int(year_str)
            else:
                year_int = int(year_str)

            if year_int < min_year or year_int > max_year:
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.FAIL,
                    detected_value=date_str,
                    reason=f"Declared manufacture/packing year '{year_str}' is not realistic. Expected year between {min_year} and {max_year}.",
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
