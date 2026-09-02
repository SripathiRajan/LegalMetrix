from datetime import datetime
from app.validators.date_validator import DateValidator
from app.models.product import ProductInput, RuleDefinition, RuleStatus, SeverityLevel


def test_valid_date_pass():
    validator = DateValidator()
    rule = RuleDefinition(
        rule_id="LMPC_RULE_6_1_D",
        field_name="date_declaration",
        mandatory=True,
        title="Month and Year of Manufacture",
        description="Month and Year of Manufacture",
        legal_reference="Rule 6(1)(d)",
        declaration_name="Month and Year of Manufacture",
        validation_type="date"
    )
    result = validator.validate(ProductInput(date_declaration="03/2024"), rule)
    assert result.status == RuleStatus.PASS


def test_future_invalid_year_fail():
    validator = DateValidator()
    rule = RuleDefinition(
        rule_id="LMPC_RULE_6_1_D",
        field_name="date_declaration",
        mandatory=True,
        title="Month and Year of Manufacture",
        description="Month and Year of Manufacture",
        legal_reference="Rule 6(1)(d)",
        declaration_name="Month and Year of Manufacture",
        validation_type="date"
    )
    current_year = datetime.now().year
    expected_max_year = current_year + 1

    result = validator.validate(ProductInput(date_declaration="01/2089"), rule)
    assert result.status == RuleStatus.FAIL
    assert "2089" in result.reason
    assert f"Expected year between 2015 and {expected_max_year}" in result.reason


def test_very_old_year_fail():
    validator = DateValidator()
    rule = RuleDefinition(
        rule_id="LMPC_RULE_6_1_D",
        field_name="date_declaration",
        mandatory=True,
        title="Month and Year of Manufacture",
        description="Month and Year of Manufacture",
        legal_reference="Rule 6(1)(d)",
        declaration_name="Month and Year of Manufacture",
        validation_type="date"
    )
    current_year = datetime.now().year
    expected_max_year = current_year + 1

    result = validator.validate(ProductInput(date_declaration="01/1995"), rule)
    assert result.status == RuleStatus.FAIL
    assert "1995" in result.reason
    assert f"Expected year between 2015 and {expected_max_year}" in result.reason


def test_missing_date_mandatory_fail():
    validator = DateValidator()
    rule = RuleDefinition(
        rule_id="LMPC_RULE_6_1_D",
        field_name="date_declaration",
        mandatory=True,
        title="Month and Year of Manufacture",
        description="Month and Year of Manufacture",
        legal_reference="Rule 6(1)(d)",
        declaration_name="Month and Year of Manufacture",
        validation_type="date"
    )
    result = validator.validate(ProductInput(date_declaration=None), rule)
    assert result.status == RuleStatus.FAIL
    assert "missing" in result.reason.lower()
