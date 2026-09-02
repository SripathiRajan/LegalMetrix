import re
from typing import Optional
from app.models.product import ProductInput, RuleDefinition, RuleCheckResult, RuleStatus, SeverityLevel
from app.validators.base import BaseValidator


class ConsumerCareValidator(BaseValidator):
    """
    Validator for Consumer Care details per Rule 6(1)(g) and Rule 6(8)
    of Legal Metrology (Packaged Commodities) Rules, 2011.
    """

    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    PHONE_PATTERN = re.compile(r'(?:\+?91[\-\s]?)?(?:1800[\-\s]?[0-9]{3,4}[\-\s]?[0-9]{3,4}|[6-9][0-9]{9}|\d{3,5}[\-\s]?\d{6,8})')

    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        # Check individual specific consumer care fields or the consolidated consumer_care string
        phone = product.consumer_care_phone
        email = product.consumer_care_email
        address = product.consumer_care_address
        consolidated = product.consumer_care

        all_text = " ".join(filter(None, [phone, email, address, consolidated])).strip()

        if not all_text:
            return self.create_result(
                rule=rule,
                status=RuleStatus.FAIL,
                detected_value=None,
                reason="Consumer care contact details (phone/email/address) are completely missing. Mandatory under Rule 6(1)(g) & Rule 6(8).",
                severity=SeverityLevel.HIGH
            )

        has_email = bool(email and self.EMAIL_PATTERN.search(email)) or bool(self.EMAIL_PATTERN.search(all_text))
        has_phone = bool(phone and self.PHONE_PATTERN.search(phone)) or bool(self.PHONE_PATTERN.search(all_text))
        has_address = bool(address and len(str(address).strip()) > 3)

        detected_channels = []
        if has_phone:
            detected_channels.append("telephone / toll-free")
        if has_email:
            detected_channels.append("email")
        if has_address:
            detected_channels.append("contact address")

        detected_val_str = (
            consolidated if consolidated else f"Phone: {phone or 'N/A'}, Email: {email or 'N/A'}"
        )

        # Rule 6(8) specifies: Name, address, telephone number and e-mail address of the person/office
        if has_phone and has_email:
            return self.create_result(
                rule=rule,
                status=RuleStatus.PASS,
                detected_value=detected_val_str,
                reason=f"Comprehensive consumer care details provided ({', '.join(detected_channels)}) satisfying Rule 6(1)(g) & Rule 6(8).",
                severity=SeverityLevel.HIGH,
                metadata={"has_phone": has_phone, "has_email": has_email, "has_address": has_address}
            )
        elif has_phone or has_email or has_address:
            # Partial consumer care (e.g. only phone number or only email)
            return self.create_result(
                rule=rule,
                status=RuleStatus.WARNING,
                detected_value=detected_val_str,
                reason=f"Partial consumer care info found ({', '.join(detected_channels)}). Rule 6(8) recommends multiple channels (name, phone, email, address).",
                severity=SeverityLevel.MEDIUM,
                metadata={"has_phone": has_phone, "has_email": has_email, "has_address": has_address}
            )

        # Some text exists, but no clear phone/email was parsed
        if len(all_text) >= 5:
            return self.create_result(
                rule=rule,
                status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
                detected_value=detected_val_str,
                reason=f"Consumer care text '{all_text}' detected, but standard phone or email pattern could not be verified automatically.",
                severity=SeverityLevel.MEDIUM
            )

        return self.create_result(
            rule=rule,
            status=RuleStatus.FAIL,
            detected_value=all_text,
            reason="Invalid consumer care declaration. Does not contain recognizable contact number or email.",
            severity=SeverityLevel.HIGH
        )
