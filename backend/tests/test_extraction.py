import pytest
from app.models.extracted_product import OCRResult, OCRRegion
from app.extraction.declaration_extractor import DeclarationExtractor
from app.extraction.normalizer import FieldNormalizer
from app.models.product import OverallComplianceStatus, RuleStatus
from app.rules.rule_engine import RuleEngine


@pytest.fixture
def extractor():
    return DeclarationExtractor()


@pytest.fixture
def normalizer():
    return FieldNormalizer()


# 1. Clear package OCR extraction
def test_clear_package_extraction(extractor):
    sample_text = """
ABC Premium Biscuits
Manufactured & Marketed by: ABC Foods Private Limited, Plot 14, SIDCO Estate, Madurai, Tamil Nadu 625001
Net Qty: 200 g
MRP Rs. 60.00 (incl. of all taxes)
Date of Pkg: 06/2026
Best Before: 6 months from packaging
Consumer Care: 1800-123-4567 email: support@abcfoods.com
Country of Origin: India
"""
    regions = [
        OCRRegion(text="ABC Premium Biscuits", confidence=0.98, bounding_box=[[10, 10], [200, 10], [200, 30], [10, 30]]),
        OCRRegion(text="Manufactured & Marketed by: ABC Foods Private Limited, Plot 14, SIDCO Estate, Madurai, Tamil Nadu 625001", confidence=0.96, bounding_box=[[10, 40], [500, 40], [500, 60], [10, 60]]),
        OCRRegion(text="Net Qty: 200 g", confidence=0.99, bounding_box=[[10, 70], [150, 70], [150, 90], [10, 90]]),
        OCRRegion(text="MRP Rs. 60.00 (incl. of all taxes)", confidence=0.97, bounding_box=[[10, 100], [280, 100], [280, 120], [10, 120]]),
        OCRRegion(text="Date of Pkg: 06/2026", confidence=0.95, bounding_box=[[10, 130], [180, 130], [180, 150], [10, 150]]),
        OCRRegion(text="Best Before: 6 months from packaging", confidence=0.94, bounding_box=[[10, 160], [250, 160], [250, 180], [10, 180]]),
        OCRRegion(text="Consumer Care: 1800-123-4567 email: support@abcfoods.com", confidence=0.96, bounding_box=[[10, 190], [380, 190], [380, 210], [10, 210]]),
        OCRRegion(text="Country of Origin: India", confidence=0.98, bounding_box=[[10, 220], [200, 220], [200, 240], [10, 240]])
    ]

    ocr_res = OCRResult(raw_text=sample_text, regions=regions, average_confidence=0.966)
    extracted = extractor.extract(ocr_res)

    assert extracted.product_name.is_detected
    assert "ABC Premium Biscuits" in extracted.product_name.value
    assert extracted.manufacturer_name.is_detected
    assert "ABC Foods" in extracted.manufacturer_name.value
    assert "Tamil Nadu" in extracted.manufacturer_address.value
    assert extracted.net_quantity.value == "200 g"
    assert "₹60" in extracted.mrp.value
    assert "06/2026" in extracted.date_declaration.value
    assert extracted.consumer_care_phone.value == "1800-123-4567"
    assert extracted.consumer_care_email.value == "support@abcfoods.com"
    assert extracted.country_of_origin.value == "India"
    assert not extracted.is_imported


# 2. MRP variations extraction and normalization
def test_mrp_variations_extraction(extractor):
    variations = [
        ("MRP ₹50", "₹50"),
        ("MRP Rs. 50", "₹50"),
        ("M.R.P. Rs 50", "₹50"),
        ("Maximum Retail Price: ₹50.00", "₹50.00"),
        ("MRP: 50.00", "₹50.00"),
        ("Rs. 100.00 (incl. of all taxes)", "₹100.00 (incl. of all taxes)")
    ]

    for raw, expected in variations:
        ocr_res = OCRResult(
            raw_text=f"Sample Product\n{raw}\nNet Qty 100 g",
            regions=[OCRRegion(text=raw, confidence=0.95, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]])]
        )
        extracted = extractor.extract(ocr_res)
        assert extracted.mrp.is_detected
        assert expected.split()[0] in extracted.mrp.value


# 3. Net quantity variations extraction without modifying non-standard units
def test_net_quantity_extraction(extractor):
    # Standard units
    standard_cases = ["100 g", "100g", "500 g", "1 kg", "1 L", "500 ml", "10 N"]
    for sc in standard_cases:
        ocr_res = OCRResult(
            raw_text=f"Product\nNet Qty: {sc}\nMRP ₹50",
            regions=[OCRRegion(text=f"Net Qty: {sc}", confidence=0.96, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]])]
        )
        extracted = extractor.extract(ocr_res)
        assert extracted.net_quantity.is_detected
        assert sc.replace(" ", "") in extracted.net_quantity.value.replace(" ", "")

    # Non-standard / illegal units - must preserve unit character
    non_standard_cases = ["100 gms", "5 kgs", "2 ltrs"]
    for nsc in non_standard_cases:
        ocr_res = OCRResult(
            raw_text=f"Product\nNet Wt: {nsc}\nMRP ₹50",
            regions=[OCRRegion(text=f"Net Wt: {nsc}", confidence=0.96, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]])]
        )
        extracted = extractor.extract(ocr_res)
        assert extracted.net_quantity.is_detected
        # Verify the non-standard unit wasn't silently converted
        assert ("gms" in extracted.net_quantity.value or "kgs" in extracted.net_quantity.value or "ltrs" in extracted.net_quantity.value)


# 4. Date extraction
def test_date_extraction_variations(extractor):
    date_cases = [
        ("06/2026", "06/2026"),
        ("06-2026", "06/2026"),
        ("June 2026", "06/2026"),
        ("Packed: 06/2026", "06/2026"),
        ("Mfd: 06/2026", "06/2026"),
        ("Pkd 12/25", "12/2025")
    ]

    for raw, expected in date_cases:
        ocr_res = OCRResult(
            raw_text=f"Product\n{raw}\nMRP ₹50",
            regions=[OCRRegion(text=raw, confidence=0.94, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]])]
        )
        extracted = extractor.extract(ocr_res)
        assert extracted.date_declaration.is_detected
        assert expected in extracted.date_declaration.value


# 5. Manufacturer and Packer context extraction
def test_manufacturer_and_packer_extraction(extractor):
    sample = """
Brand Delight
Manufactured by: Delight Confectionery Ltd, Industrial Area, Pune, Maharashtra 411018
Packed by: Swift Packing Solutions, Andheri, Mumbai 400069
Net Wt: 150 g
MRP: ₹75
"""
    ocr_res = OCRResult(raw_text=sample, regions=[])
    extracted = extractor.extract(ocr_res)

    assert extracted.manufacturer_name.is_detected
    assert "Delight Confectionery" in extracted.manufacturer_name.value
    assert "Pune" in extracted.manufacturer_address.value
    assert extracted.packer_name.is_detected
    assert "Swift Packing" in extracted.packer_name.value


# 6. Consumer Care Extraction
def test_consumer_care_extraction(extractor):
    sample = """
Soap Bar
Net Qty: 125 g
MRP ₹40
Consumer Care Toll Free: 1800-456-7890 Email: care@consumer.in
Plot 5, Whitefield, Bengaluru
"""
    ocr_res = OCRResult(raw_text=sample, regions=[])
    extracted = extractor.extract(ocr_res)

    assert extracted.consumer_care_phone.is_detected
    assert extracted.consumer_care_phone.value == "1800-456-7890"
    assert extracted.consumer_care_email.is_detected
    assert extracted.consumer_care_email.value == "care@consumer.in"


# 7. Imported product extraction
def test_imported_product_extraction(extractor):
    sample = """
Swiss Luxury Chocolates
Made in Switzerland
Imported by: Apex Global Trading Pvt Ltd, Connaught Place, New Delhi 110001
Net Weight: 100 g
MRP: ₹350
Mfd: 01/2026
"""
    ocr_res = OCRResult(raw_text=sample, regions=[])
    extracted = extractor.extract(ocr_res)

    assert extracted.country_of_origin.is_detected
    assert "Switzerland" in extracted.country_of_origin.value
    assert extracted.importer_name.is_detected
    assert "Apex Global" in extracted.importer_name.value
    assert extracted.is_imported


# 8. Missing declarations
def test_missing_declarations_extraction(extractor):
    # Only product name and generic text present
    sample = """
Generic Product
Random descriptive text without any statutory declarations
"""
    ocr_res = OCRResult(raw_text=sample, regions=[])
    extracted = extractor.extract(ocr_res)

    assert not extracted.mrp.is_detected
    assert not extracted.net_quantity.is_detected
    assert not extracted.manufacturer_name.is_detected
    assert not extracted.date_declaration.is_detected
    assert not extracted.consumer_care.is_detected


# 9. OCR Confidence propagation
def test_ocr_confidence_propagation(extractor):
    ocr_res = OCRResult(
        raw_text="Net Qty: 500 g\nMRP: ₹99",
        regions=[
            OCRRegion(text="Net Qty: 500 g", confidence=0.92, bounding_box=[[0, 0], [100, 0], [100, 20], [0, 20]]),
            OCRRegion(text="MRP: ₹99", confidence=0.74, bounding_box=[[0, 30], [80, 30], [80, 50], [0, 50]])
        ],
        average_confidence=0.83
    )
    extracted = extractor.extract(ocr_res)
    assert extracted.net_quantity.confidence == 0.92
    assert extracted.mrp.confidence == 0.74
    assert len(extracted.net_quantity.bounding_boxes) > 0


# 10. End-to-end integration with Rule Engine
def test_extracted_data_to_rule_engine_integration(extractor):
    sample = """
Organic Wheat Flour
Manufactured by: Green Fields Agro Ltd, Phase 2, Ludhiana, Punjab 141001
Net Qty: 5 kg
MRP ₹240.00 incl. of all taxes
Pkd: 05/2026
Customer Care: 1800-999-8888 care@greenfields.com
Country of Origin: India
"""
    ocr_res = OCRResult(raw_text=sample, regions=[])
    extracted = extractor.extract(ocr_res)

    product_input = extracted.to_product_input(raw_text=sample)
    rule_engine = RuleEngine()
    compliance_res = rule_engine.evaluate(product_input)

    assert compliance_res.overall_status == OverallComplianceStatus.COMPLIANT
    assert compliance_res.failed == 0
    assert compliance_res.compliance_score == 100.0
