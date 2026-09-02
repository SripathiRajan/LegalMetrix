from abc import ABC, abstractmethod
from typing import Optional
from app.models.product import ProductInput, RuleDefinition, RuleCheckResult, RuleStatus, SeverityLevel


class BaseValidator(ABC):
    """
    Abstract base class for all Legal Metrology declaration validators.
    """

    @abstractmethod
    def validate(self, product: ProductInput, rule: RuleDefinition) -> RuleCheckResult:
        """
        Validate a specific declaration against the given rule.
        """
        pass

    def create_result(
        self,
        rule: RuleDefinition,
        status: RuleStatus,
        detected_value: Optional[str],
        reason: str,
        severity: Optional[SeverityLevel] = None,
        metadata: Optional[dict] = None
    ) -> RuleCheckResult:
        return RuleCheckResult(
            rule_id=rule.rule_id,
            declaration=rule.declaration_name,
            status=status,
            detected_value=detected_value,
            reason=reason,
            legal_reference=rule.legal_reference,
            severity=severity or rule.severity,
            metadata=metadata
        )
