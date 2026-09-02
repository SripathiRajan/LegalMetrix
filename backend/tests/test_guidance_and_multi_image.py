from app.models.product import ProductInput, RuleStatus
from app.services.compliance_service import ComplianceService, GUIDANCE_NOTE_TEXT
from app.services.pdf_report_generator import PDFReportGenerator


def test_missing_critical_fields_guidance_note():
    service = ComplianceService()

    # Product missing MRP & Manufacturer & Consumer Care (3 missing)
    product_missing_all = ProductInput(
        product_name="Sample Product",
        net_quantity="100 g",
        date_declaration="06/2026",
        mrp=None,
        manufacturer_name=None,
        consumer_care=None
    )

    res_all = service.check_compliance(product_missing_all)
    assert res_all.guidance_note == GUIDANCE_NOTE_TEXT
    assert "Possible cause: Only back panel / nutrition side was captured." in res_all.summary

    # Product missing MRP & Consumer Care (2 missing)
    product_missing_two = ProductInput(
        product_name="Sample Product",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, TN",
        net_quantity="100 g",
        date_declaration="06/2026",
        mrp=None,
        consumer_care=None
    )

    res_two = service.check_compliance(product_missing_two)
    assert res_two.guidance_note == GUIDANCE_NOTE_TEXT

    # Product missing only MRP (1 missing out of 3 critical)
    product_missing_one = ProductInput(
        product_name="Sample Product",
        manufacturer_name="ABC Foods Pvt Ltd",
        manufacturer_address="Madurai, TN",
        consumer_care="support@abcfoods.com",
        net_quantity="100 g",
        date_declaration="06/2026",
        mrp=None
    )

    res_one = service.check_compliance(product_missing_one)
    assert res_one.guidance_note is None


def test_pdf_report_includes_guidance_note():
    service = ComplianceService()
    generator = PDFReportGenerator()

    product_missing = ProductInput(
        product_name="Sample Product",
        net_quantity="100 g",
        date_declaration="06/2026",
        mrp=None,
        manufacturer_name=None,
        consumer_care=None
    )

    compliance_res = service.check_compliance(product_missing)
    assert compliance_res.guidance_note is not None

    pdf_bytes = generator.generate_report(
        compliance_result=compliance_res.model_dump(),
        scan_id=999,
        product_name="Sample Product"
    )

    assert len(pdf_bytes) > 0
    # PDF header bytes
    assert pdf_bytes.startswith(b"%PDF")


def test_multi_extracted_data_merge():
    from app.models.extracted_product import ExtractedProductData, ExtractedField

    service = ComplianceService()

    ext1 = ExtractedProductData(
        product_name=ExtractedField(value="Digestive Biscuits", confidence=0.9, is_detected=True),
        mrp=ExtractedField(value="₹50.00", confidence=0.95, is_detected=True)
    )

    ext2 = ExtractedProductData(
        manufacturer_name=ExtractedField(value="ABC Foods Pvt Ltd", confidence=0.88, is_detected=True),
        consumer_care=ExtractedField(value="care@abcfoods.com", confidence=0.85, is_detected=True)
    )

    merged = service._merge_extracted_data([ext1, ext2])
    assert merged.product_name.value == "Digestive Biscuits"
    assert merged.mrp.value == "₹50.00"
    assert merged.manufacturer_name.value == "ABC Foods Pvt Ltd"
    assert merged.consumer_care.value == "care@abcfoods.com"
