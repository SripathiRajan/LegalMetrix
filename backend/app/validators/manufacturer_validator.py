import re
from typing import Optional
from app.models.product import ProductInput, RuleDefinition, RuleCheckResult, RuleStatus, SeverityLevel
from app.validators.base import BaseValidator


class ManufacturerValidator(BaseValidator):
    """
    Validator for Manufacturer / Packer / Importer details per Rule 6(1)(a),
    Rule 6(1)(ab), and Rule 6(1)(da) of Legal Metrology (Packaged Commodities) Rules, 2011.
    """

    # Common Indian states and union territories to verify address completeness
    INDIAN_STATES = [
        "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
        "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
        "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
        "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
        "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
        "delhi", "puducherry", "chandigarh", "jammu & kashmir", "jammu and kashmir",
        "ladakh"
    ]

    PINCODE_PATTERN = re.compile(r'\b[1-9][0-9]{5}\b')

    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        is_importer_rule = "IMPORTER" in rule.rule_id

        if is_importer_rule:
            # Importer details check
            if not product.is_imported:
                return self.create_result(
                    rule=rule,
                    status=RuleStatus.NOT_APPLICABLE,
                    detected_value=None,
                    reason="Product is not marked as imported. Importer declaration is not applicable.",
                    severity=SeverityLevel.LOW
                )

            name = product.importer_name
            address = product.importer_address
            entity_label = "Importer"
        else:
            # Manufacturer or Packer details check
            name = product.manufacturer_name or product.packer_name
            address = product.manufacturer_address or product.packer_address
            entity_label = "Manufacturer / Packer"

        has_name = bool(name and str(name).strip())
        has_address = bool(address and str(address).strip())

        detected_summary = []
        if has_name:
            detected_summary.append(f"Name: {name.strip()}")
        if has_address:
            detected_summary.append(f"Address: {address.strip()}")
        detected_val_str = " | ".join(detected_summary) if detected_summary else None

        # If both name and address are missing
        if not has_name and not has_address:
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=None,
                reason=f"{entity_label} name and address are completely missing. Mandatory under {rule.legal_reference}.",
                severity=SeverityLevel.HIGH
            )

        # Missing address
        if has_name and not has_address:
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=detected_val_str,
                reason=f"{entity_label} name is present ('{name}'), but complete address is missing. Mandatory under Rule 6(1)(a).",
                severity=SeverityLevel.HIGH
            )

        # Missing name
        if not has_name and has_address:
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=detected_val_str,
                reason=f"{entity_label} address is present ('{address}'), but entity name is missing. Mandatory under Rule 6(1)(a).",
                severity=SeverityLevel.HIGH
            )

        # Both name and address present - verify address completeness
        addr_lower = address.lower()
        has_pincode = bool(self.PINCODE_PATTERN.search(addr_lower))
        has_state_or_city = any(st in addr_lower for st in self.INDIAN_STATES) or len(address.split(',')) >= 2 or len(address.split()) >= 3

        if len(address.strip()) < 5:
            return self.create_result(
                rule=rule,
                status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
                detected_value=detected_val_str,
                reason=f"{entity_label} address '{address}' appears too brief to be a complete postal address. Human verification required.",
                severity=SeverityLevel.MEDIUM
            )

        if has_pincode or has_state_or_city:
            return self.create_result(
                rule=rule,
                status=RuleStatus.PASS,
                detected_value=detected_val_str,
                reason=f"Valid {entity_label} name and address declared per Rule 6(1)(a) / Rule 6(1)(ab).",
                severity=SeverityLevel.HIGH,
                metadata={"has_pincode": has_pincode, "has_state_or_city": has_state_or_city}
            )

        return self.create_result(
            rule=rule,
            status=RuleStatus.WARNING,
            detected_value=detected_val_str,
            reason=f"{entity_label} name and address provided, but address details may lack city/state/pin code clarity.",
            severity=SeverityLevel.LOW
        )
