from app.validators.commodity_validator import CommodityNameValidator
from app.models.product import ProductInput, RuleDefinition, RuleStatus
from app.extraction.normalizer import FieldNormalizer


def test_code_like_string_detection():
    # Codes that should be detected as code-like
    assert FieldNormalizer.is_code_like("S60017") is True
    assert FieldNormalizer.is_code_like("AB1234") is True
    assert FieldNormalizer.is_code_like("98765") is True
    assert FieldNormalizer.is_code_like("A1") is True
    assert FieldNormalizer.is_code_like("P-10023") is True

    # Legitimate names that should NOT be rejected
    assert FieldNormalizer.is_code_like("Tea") is False
    assert FieldNormalizer.is_code_like("Oil") is False
    assert FieldNormalizer.is_code_like("Pen") is False
    assert FieldNormalizer.is_code_like("Biscuits") is False
    assert FieldNormalizer.is_code_like("A4 Paper") is False
    assert FieldNormalizer.is_code_like("V8 Juice") is False


def test_commodity_validator_rejects_product_code():
    validator = CommodityNameValidator()
    rule = RuleDefinition(
        rule_id="LMPC_RULE_6_1_B",
        field_name="generic_name",
        mandatory=True,
        title="Generic/Common Name of Commodity",
        description="Name of Commodity",
        legal_reference="Rule 6(1)(b)",
        declaration_name="Generic/Common Name of Commodity",
        validation_type="text"
    )

    # Product code "S60017" -> FAIL
    res_code = validator.validate(ProductInput(generic_name="S60017"), rule)
    assert res_code.status == RuleStatus.FAIL
    assert "S60017" in res_code.reason
    assert "product/batch code" in res_code.reason

    # Legitimate short name "Tea" -> PASS
    res_valid = validator.validate(ProductInput(generic_name="Tea"), rule)
    assert res_valid.status == RuleStatus.PASS

    # Legitimate name "Digestive Biscuits" -> PASS
    res_biscuits = validator.validate(ProductInput(generic_name="Digestive Biscuits"), rule)
    assert res_biscuits.status == RuleStatus.PASS
