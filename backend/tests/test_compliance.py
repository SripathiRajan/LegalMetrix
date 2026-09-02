import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.product import (
    ProductInput,
    RuleStatus,
    OverallComplianceStatus,
    ComplianceResponse
)
from app.rules.rule_engine import RuleEngine

client = TestClient(app)
engine = RuleEngine()


def get_rule_result(response: ComplianceResponse, rule_id: str):
    """Helper to find result for a specific rule_id."""
    for res in response.results:
        if res.rule_id == rule_id:
            return res
    return None


# 1. Completely filled product (Fully Compliant)
def test_completely_filled_product():
    payload = {
        "product_name": "ABC Biscuits",
        "generic_name": "Biscuits",
        "manufacturer_name": "ABC Foods Pvt Ltd",
        "manufacturer_address": "Plot 12, Industrial Estate, Madurai, Tamil Nadu - 625001",
        "net_quantity": "100 g",
        "mrp": "MRP ₹ 50.00 incl. of all taxes",
        "date_declaration": "06/2026",
        "consumer_care": "Care Manager, ABC Foods, support@abcfoods.com, 1800-123-4567, Madurai",
        "consumer_care_email": "support@abcfoods.com",
        "consumer_care_phone": "1800-123-4567",
        "consumer_care_address": "Plot 12, Industrial Estate, Madurai, Tamil Nadu - 625001",
        "country_of_origin": "India",
        "is_imported": False
    }

    resp = client.post("/api/compliance/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["overall_status"] == OverallComplianceStatus.COMPLIANT
    assert data["failed"] == 0
    assert data["compliance_score"] == 100.0
    assert len(data["violations"]) == 0

    # Verify key rules are PASS
    rule_ids = {r["rule_id"]: r["status"] for r in data["results"]}
    assert rule_ids["LMPC_RULE_6_1_A"] == RuleStatus.PASS
    assert rule_ids["LMPC_RULE_6_1_B"] == RuleStatus.PASS
    assert rule_ids["LMPC_RULE_6_1_C"] == RuleStatus.PASS
    assert rule_ids["LMPC_RULE_6_1_D"] == RuleStatus.PASS
    assert rule_ids["LMPC_RULE_6_1_E"] == RuleStatus.PASS
    assert rule_ids["LMPC_RULE_6_1_G"] == RuleStatus.PASS


# 2. Missing MRP
def test_missing_mrp():
    product = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="100 g",
        mrp=None,  # Missing MRP
        date_declaration="06/2026",
        consumer_care="support@abc.com 1800-123-4567"
    )

    assessment = engine.evaluate(product)
    assert assessment.overall_status == OverallComplianceStatus.NON_COMPLIANT
    assert assessment.failed >= 1

    mrp_res = get_rule_result(assessment, "LMPC_RULE_6_1_E")
    assert mrp_res is not None
    assert mrp_res.status == RuleStatus.FAIL
    assert "Rule 6(1)(e)" in mrp_res.legal_reference


# 3. Missing Net Quantity
def test_missing_net_quantity():
    product = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="",  # Empty/missing quantity
        mrp="₹50 incl of all taxes",
        date_declaration="06/2026",
        consumer_care="support@abc.com 1800-123-4567"
    )

    assessment = engine.evaluate(product)
    assert assessment.overall_status == OverallComplianceStatus.NON_COMPLIANT
    qty_res = get_rule_result(assessment, "LMPC_RULE_6_1_C")
    assert qty_res is not None
    assert qty_res.status == RuleStatus.FAIL
    assert "Rule 6(1)(c)" in qty_res.legal_reference


# 4. Missing Manufacturer Information
def test_missing_manufacturer_info():
    # Both name & address missing
    product = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name=None,
        manufacturer_address=None,
        net_quantity="100 g",
        mrp="₹50",
        date_declaration="06/2026",
        consumer_care="support@abc.com 1800-123-4567"
    )

    assessment = engine.evaluate(product)
    assert assessment.overall_status == OverallComplianceStatus.NON_COMPLIANT
    mfg_res = get_rule_result(assessment, "LMPC_RULE_6_1_A")
    assert mfg_res is not None
    assert mfg_res.status == RuleStatus.FAIL

    # Name present but address missing
    product_no_addr = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address=None,
        net_quantity="100 g",
        mrp="₹50",
        date_declaration="06/2026",
        consumer_care="support@abc.com 1800-123-4567"
    )
    assessment_no_addr = engine.evaluate(product_no_addr)
    mfg_res2 = get_rule_result(assessment_no_addr, "LMPC_RULE_6_1_A")
    assert mfg_res2.status == RuleStatus.FAIL


# 5. Missing Consumer Care Information
def test_missing_consumer_care():
    product = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="100 g",
        mrp="₹50",
        date_declaration="06/2026",
        consumer_care=None,
        consumer_care_email=None,
        consumer_care_phone=None
    )

    assessment = engine.evaluate(product)
    assert assessment.overall_status == OverallComplianceStatus.NON_COMPLIANT
    cc_res = get_rule_result(assessment, "LMPC_RULE_6_1_G")
    assert cc_res is not None
    assert cc_res.status == RuleStatus.FAIL
    assert "Rule 6(1)(g)" in cc_res.legal_reference


# 6. Imported Product Rules
def test_imported_product_compliance():
    # Imported product with missing country of origin and importer
    product_imported_missing = ProductInput(
        product_name="Imported Chocolate",
        is_imported=True,
        country_of_origin=None,
        importer_name=None,
        importer_address=None,
        net_quantity="200 g",
        mrp="₹250 incl of all taxes",
        date_declaration="01/2026",
        consumer_care="1800-555-5555 care@importer.com"
    )
    assessment1 = engine.evaluate(product_imported_missing)
    origin_res = get_rule_result(assessment1, "LMPC_RULE_6_1_DA_ORIGIN")
    importer_res = get_rule_result(assessment1, "LMPC_RULE_6_1_DA_IMPORTER")
    assert origin_res.status == RuleStatus.FAIL
    assert importer_res.status == RuleStatus.FAIL

    # Imported product properly filled
    product_imported_valid = ProductInput(
        product_name="Imported Swiss Chocolate",
        is_imported=True,
        country_of_origin="Switzerland",
        importer_name="Global Imports India Pvt Ltd",
        importer_address="Andheri East, Mumbai, Maharashtra 400069",
        net_quantity="200 g",
        mrp="₹250.00 incl. of all taxes",
        date_declaration="01/2026",
        consumer_care="1800-555-5555 care@globalimports.in"
    )
    assessment2 = engine.evaluate(product_imported_valid)
    origin_res2 = get_rule_result(assessment2, "LMPC_RULE_6_1_DA_ORIGIN")
    importer_res2 = get_rule_result(assessment2, "LMPC_RULE_6_1_DA_IMPORTER")
    assert origin_res2.status == RuleStatus.PASS
    assert importer_res2.status == RuleStatus.PASS


# 7. Invalid MRP Format
def test_invalid_mrp_format():
    # Non-numeric / zero / free MRP
    product_zero = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="100 g",
        mrp="FREE / Rs 0",
        date_declaration="06/2026",
        consumer_care="support@abc.com 1800-123-4567"
    )
    assessment = engine.evaluate(product_zero)
    mrp_res = get_rule_result(assessment, "LMPC_RULE_6_1_E")
    assert mrp_res.status == RuleStatus.FAIL

    # Warning on missing 'inclusive of all taxes' or missing symbol
    product_warning = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="100 g",
        mrp="50.00",  # No currency symbol, no incl taxes
        date_declaration="06/2026",
        consumer_care="support@abc.com 1800-123-4567"
    )
    assessment_warn = engine.evaluate(product_warning)
    mrp_res_warn = get_rule_result(assessment_warn, "LMPC_RULE_6_1_E")
    assert mrp_res_warn.status == RuleStatus.WARNING


# 8. Invalid Quantity Format
def test_invalid_quantity_format():
    # Non-standard unit (e.g. 'gms' instead of standard 'g' per Rule 13)
    product_non_standard = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="100 gms",
        mrp="₹50 incl. of all taxes",
        date_declaration="06/2026",
        consumer_care="support@abc.com 1800-123-4567"
    )
    assessment = engine.evaluate(product_non_standard)
    qty_res = get_rule_result(assessment, "LMPC_RULE_6_1_C")
    assert qty_res.status == RuleStatus.WARNING
    assert "Rule 13" in qty_res.reason

    # Totally unrecognized unit
    product_invalid = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="XYZ_INVALID",
        mrp="₹50 incl. of all taxes",
        date_declaration="06/2026",
        consumer_care="support@abc.com 1800-123-4567"
    )
    assessment_inv = engine.evaluate(product_invalid)
    qty_res_inv = get_rule_result(assessment_inv, "LMPC_RULE_6_1_C")
    assert qty_res_inv.status == RuleStatus.FAIL


# 9. Missing / Ambiguous Date Declaration
def test_missing_and_ambiguous_date():
    # Missing date
    product_missing = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="100 g",
        mrp="₹50 incl. of all taxes",
        date_declaration=None,
        consumer_care="support@abc.com 1800-123-4567"
    )
    assessment_missing = engine.evaluate(product_missing)
    date_res_missing = get_rule_result(assessment_missing, "LMPC_RULE_6_1_D")
    assert date_res_missing.status == RuleStatus.FAIL

    # Ambiguous date (short fragment or non-standard string)
    product_ambiguous = ProductInput(
        product_name="ABC Biscuits",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, Tamil Nadu 625001",
        net_quantity="100 g",
        mrp="₹50 incl. of all taxes",
        date_declaration="99/88/77",
        consumer_care="support@abc.com 1800-123-4567"
    )
    assessment_ambiguous = engine.evaluate(product_ambiguous)
    date_res_ambiguous = get_rule_result(assessment_ambiguous, "LMPC_RULE_6_1_D")
    assert date_res_ambiguous.status == RuleStatus.REQUIRES_HUMAN_VERIFICATION


# 10. E-Commerce Listing Analysis Mode Test
def test_ecommerce_listing_mode_analysis():
    from app.services.compliance_service import ComplianceService
    from PIL import Image
    import io

    # Create dummy image bytes
    img = Image.new("RGB", (300, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    service = ComplianceService()
    res = service.analyze_image_end_to_end(img_bytes, input_type="ecommerce_listing", persist=False)
    
    assert res.compliance_result.input_type == "ecommerce_listing"
    assert "E-commerce Listing Analysis Mode" in res.compliance_result.summary

