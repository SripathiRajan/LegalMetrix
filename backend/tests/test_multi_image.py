import pytest
from app.models.extracted_product import ExtractedProductData, ExtractedField
from app.services.compliance_service import ComplianceService


def test_multi_image_fields_merging_synthetic_case_a():
    """
    Case A: Field A (MRP) only in Image 1, Field B (Manufacturer) only in Image 2.
    Merged result must contain both fields.
    """
    service = ComplianceService()

    ext_image_1 = ExtractedProductData(
        mrp=ExtractedField(value="₹150.00", confidence=0.92, is_detected=True),
        product_name=ExtractedField(value="Premium Almonds", confidence=0.88, is_detected=True)
    )

    ext_image_2 = ExtractedProductData(
        manufacturer_name=ExtractedField(value="NutriFoods India Pvt Ltd", confidence=0.95, is_detected=True),
        consumer_care=ExtractedField(value="support@nutrifoods.in", confidence=0.91, is_detected=True)
    )

    merged, sources = service._merge_extracted_data_with_sources([ext_image_1, ext_image_2])

    assert merged.mrp.value == "₹150.00"
    assert merged.product_name.value == "Premium Almonds"
    assert merged.manufacturer_name.value == "NutriFoods India Pvt Ltd"
    assert merged.consumer_care.value == "support@nutrifoods.in"

    assert sources["mrp"] == 0
    assert sources["product_name"] == 0
    assert sources["manufacturer_name"] == 1
    assert sources["consumer_care"] == 1


def test_multi_image_confidence_ranking_synthetic_case_b():
    """
    Case B: Same field present in both images with different confidence scores.
    Higher confidence field must win.
    """
    service = ComplianceService()

    # Image 1 has lower confidence MRP
    ext_image_1 = ExtractedProductData(
        mrp=ExtractedField(value="₹99.00", confidence=0.65, is_detected=True),
        net_quantity=ExtractedField(value="500 g", confidence=0.95, is_detected=True)
    )

    # Image 2 has higher confidence MRP
    ext_image_2 = ExtractedProductData(
        mrp=ExtractedField(value="₹100.00", confidence=0.98, is_detected=True),
        net_quantity=ExtractedField(value="500 g", confidence=0.70, is_detected=True)
    )

    merged, sources = service._merge_extracted_data_with_sources([ext_image_1, ext_image_2])

    assert merged.mrp.value == "₹100.00"
    assert sources["mrp"] == 1

    assert merged.net_quantity.value == "500 g"
    assert sources["net_quantity"] == 0


def test_single_image_backward_compatibility():
    """
    Single image case must return expected fields and source index 0 for all detected fields.
    """
    service = ComplianceService()

    ext_single = ExtractedProductData(
        product_name=ExtractedField(value="Whole Wheat Flour", confidence=0.90, is_detected=True),
        mrp=ExtractedField(value="₹250.00", confidence=0.94, is_detected=True),
        net_quantity=ExtractedField(value="5 kg", confidence=0.91, is_detected=True)
    )

    merged, sources = service._merge_extracted_data_with_sources([ext_single])

    assert merged.product_name.value == "Whole Wheat Flour"
    assert merged.mrp.value == "₹250.00"
    assert merged.net_quantity.value == "5 kg"

    assert sources["product_name"] == 0
    assert sources["mrp"] == 0
    assert sources["net_quantity"] == 0
