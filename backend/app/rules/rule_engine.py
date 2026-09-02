from typing import List, Dict, Type, Optional, Any
from app.models.product import (
    ProductInput,
    RuleDefinition,
    RuleCheckResult,
    RuleStatus,
    SeverityLevel,
    ComplianceResponse,
    OverallComplianceStatus
)
from app.rules.rule_loader import RuleLoader
from app.validators.base import BaseValidator
from app.validators.mrp_validator import MRPValidator
from app.validators.quantity_validator import QuantityValidator
from app.validators.date_validator import DateValidator
from app.validators.manufacturer_validator import ManufacturerValidator
from app.validators.consumer_care_validator import ConsumerCareValidator
from app.validators.origin_validator import OriginValidator
from app.validators.commodity_validator import CommodityNameValidator, UnitSalePriceValidator


class RuleEngine:
    """
    Modular Rule Engine executing declarative Legal Metrology checks.
    Evaluates each rule independently, links visual evidence, and computes an overall compliance assessment.
    """

    # Mapping of rule_id to corresponding attribute in ExtractedProductData
    RULE_EVIDENCE_MAP = {
        "LMPC_RULE_6_1_A": "manufacturer_name",
        "LMPC_RULE_6_1_B": "commodity_name",
        "LMPC_RULE_6_1_C": "net_quantity",
        "LMPC_RULE_6_1_D": "date_declaration",
        "LMPC_RULE_6_1_DA_ORIGIN": "country_of_origin",
        "LMPC_RULE_6_1_DA_IMPORTER": "importer_name",
        "LMPC_RULE_6_1_E": "mrp",
        "LMPC_RULE_6_1_G": "consumer_care",
        "LMPC_RULE_6_1_F": "best_before",
        "LMPC_RULE_6_1_E_USP": "unit_sale_price"
    }

    def __init__(self, rule_loader: RuleLoader = None):
        self.rule_loader = rule_loader or RuleLoader()
        self.rules: List[RuleDefinition] = self.rule_loader.load_rules()

        # Map validation_type string from rules.json to validator instances
        self.validators: Dict[str, BaseValidator] = {
            "MRP_VALIDATION": MRPValidator(),
            "QUANTITY_VALIDATION": QuantityValidator(),
            "DATE_VALIDATION": DateValidator(),
            "BEST_BEFORE_VALIDATION": DateValidator(),
            "MANUFACTURER_VALIDATION": ManufacturerValidator(),
            "IMPORTER_VALIDATION": ManufacturerValidator(),
            "CONSUMER_CARE_VALIDATION": ConsumerCareValidator(),
            "ORIGIN_VALIDATION": OriginValidator(),
            "COMMODITY_NAME_VALIDATION": CommodityNameValidator(),
            "UNIT_SALE_PRICE_VALIDATION": UnitSalePriceValidator(),
        }

    def register_validator(self, validation_type: str, validator: BaseValidator):
        """Allows dynamic extension or overriding of validators."""
        self.validators[validation_type] = validator

    def _is_rule_applicable(self, product: ProductInput, rule: RuleDefinition) -> bool:
        """Determines if a conditional rule is applicable to the current product."""
        if not rule.conditional:
            return True

        if not rule.applicability_condition:
            return True

        condition = rule.applicability_condition.lower()

        # Evaluate specific known conditions
        if "is_imported == true" in condition:
            if product.is_imported or (product.country_of_origin and product.country_of_origin.strip().lower() not in ["india", "in", "ind"]):
                return True
            return False

        if "category in" in condition:
            cat = (product.category or "").lower()
            if any(c in condition for c in [f"'{cat}'", f'"{cat}"']):
                return True
            if product.best_before_date is not None:
                return True
            return False

        if "unit_sale_price is not null" in condition:
            return product.unit_sale_price is not None or product.package_type == "multi_unit"

        return True

    def evaluate_rule(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        """Evaluates a single rule against the product input."""
        # Check applicability
        if not self._is_rule_applicable(product, rule):
            return RuleCheckResult(
                rule_id=rule.rule_id,
                declaration=rule.declaration_name,
                status=RuleStatus.NOT_APPLICABLE,
                detected_value=None,
                reason="Rule is not applicable to this commodity category or configuration.",
                legal_reference=rule.legal_reference,
                severity=rule.severity
            )

        validator = self.validators.get(rule.validation_type)
        if not validator:
            return RuleCheckResult(
                rule_id=rule.rule_id,
                declaration=rule.declaration_name,
                status=RuleStatus.REQUIRES_HUMAN_VERIFICATION,
                detected_value=None,
                reason=f"No automated validator registered for '{rule.validation_type}'.",
                legal_reference=rule.legal_reference,
                severity=rule.severity
            )

        return validator.validate(product, rule)

    def evaluate(
        self,
        product: ProductInput,
        extracted_data: Optional[Any] = None,
        annotated_image: Optional[str] = None
    ) -> ComplianceResponse:
        """
        Runs all configured rules against the product input, attaches visual evidence
        from extracted declarations, and generates a comprehensive compliance response.
        """
        results: List[RuleCheckResult] = []
        violations: List[RuleCheckResult] = []

        passed_count = 0
        failed_count = 0
        warning_count = 0
        human_req_count = 0
        not_applicable_count = 0

        # Weights by severity for calculating compliance score
        severity_weights = {
            SeverityLevel.HIGH: 3.0,
            SeverityLevel.MEDIUM: 2.0,
            SeverityLevel.LOW: 1.0
        }

        total_applicable_weight = 0.0
        earned_weight = 0.0

        for rule in self.rules:
            result = self.evaluate_rule(product, rule)

            # Attach visual evidence if extracted_data is available
            if extracted_data is not None:
                field_attr = self.RULE_EVIDENCE_MAP.get(rule.rule_id)
                if field_attr and hasattr(extracted_data, field_attr):
                    ext_field = getattr(extracted_data, field_attr)
                    if ext_field and ext_field.evidence:
                        result.evidence = {
                            "source_text": ext_field.source_text,
                            "bounding_boxes": [ext_field.evidence.bounding_box] if ext_field.evidence.bounding_box else [],
                            "normalized_bbox": ext_field.evidence.normalized_bbox,
                            "ocr_confidence": ext_field.evidence.ocr_confidence,
                            "readability_status": ext_field.evidence.readability_status,
                            "text_height_pixels": ext_field.evidence.text_height_pixels,
                            "position": ext_field.evidence.position,
                            "has_evidence": ext_field.evidence.has_evidence
                        }
                    else:
                        result.evidence = {
                            "source_text": None,
                            "bounding_boxes": [],
                            "ocr_confidence": 0.0,
                            "readability_status": "UNREADABLE",
                            "has_evidence": False
                        }

            results.append(result)

            w = severity_weights.get(result.severity, 2.0)

            if result.status == RuleStatus.PASS:
                passed_count += 1
                total_applicable_weight += w
                earned_weight += w
            elif result.status == RuleStatus.FAIL:
                failed_count += 1
                total_applicable_weight += w
                violations.append(result)
            elif result.status == RuleStatus.WARNING:
                warning_count += 1
                total_applicable_weight += w
                earned_weight += (w * 0.6)  # Partial credit for minor warning
                violations.append(result)
            elif result.status == RuleStatus.REQUIRES_HUMAN_VERIFICATION:
                human_req_count += 1
                total_applicable_weight += w
                earned_weight += (w * 0.5)  # Neutral halfway for unverified
            elif result.status == RuleStatus.NOT_APPLICABLE:
                not_applicable_count += 1

        # Calculate compliance score (0-100)
        if total_applicable_weight > 0:
            compliance_score = round((earned_weight / total_applicable_weight) * 100, 1)
        else:
            compliance_score = 100.0

        # Determine overall status
        if failed_count > 0:
            overall_status = OverallComplianceStatus.NON_COMPLIANT
        elif human_req_count > 0:
            overall_status = OverallComplianceStatus.PARTIAL_COMPLIANCE_NEEDS_REVIEW
        elif warning_count > 0:
            overall_status = OverallComplianceStatus.POTENTIALLY_NON_COMPLIANT
        else:
            overall_status = OverallComplianceStatus.COMPLIANT

        return ComplianceResponse(
            overall_status=overall_status,
            compliance_score=compliance_score,
            total_checks=len(results),
            passed=passed_count,
            failed=failed_count,
            warnings=warning_count,
            human_verification_required=human_req_count,
            not_applicable=not_applicable_count,
            violations=violations,
            results=results,
            annotated_image=annotated_image
        )
