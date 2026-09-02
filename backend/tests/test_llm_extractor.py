import pytest
from app.models.extracted_product import OCRResult, OCRRegion, ExtractedProductData, ExtractedField
from app.extraction.declaration_extractor import DeclarationExtractor
from app.extraction.llm_extractor import LLMDeclarationExtractor


def test_madurai_city_disambiguation():
    sample_text = """
    Cooling Beverage 1 L
    Manufactured by: Madurai Bottling Plant Pvt Ltd, 42 Industrial Area, Madurai, Tamil Nadu 625001
    MRP Rs. 50.00 (incl. of all taxes)
    USP Rs. 0.05 / ml
    Date of Mfg: 05/2026
    """
    regions = [
        OCRRegion(text="Cooling Beverage 1 L", confidence=0.98, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]]),
        OCRRegion(text="Manufactured by: Madurai Bottling Plant Pvt Ltd, 42 Industrial Area, Madurai, Tamil Nadu 625001", confidence=0.95, bounding_box=[[0, 15], [10, 15], [10, 25], [0, 25]]),
        OCRRegion(text="MRP Rs. 50.00 (incl. of all taxes)", confidence=0.97, bounding_box=[[0, 30], [10, 30], [10, 40], [0, 40]]),
        OCRRegion(text="USP Rs. 0.05 / ml", confidence=0.96, bounding_box=[[0, 45], [10, 45], [10, 55], [0, 55]])
    ]
    ocr_res = OCRResult(raw_text=sample_text, regions=regions)
    extractor = DeclarationExtractor()
    extracted = extractor.extract(ocr_res)

    # Madurai should NOT be returned as Country of Origin
    assert extracted.country_of_origin.value == "India"
    assert not extracted.is_imported


def test_bottle_quantity_vs_usp_disambiguation():
    sample_text = """
    Water Bottle 1 Liter
    USP Rs. 0.1 / m
    MRP Rs. 20.00
    Mfg Date: 01/2026
    Manufactured in Madurai
    """
    regions = [
        OCRRegion(text="Water Bottle 1 Liter", confidence=0.98, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]]),
        OCRRegion(text="USP Rs. 0.1 / m", confidence=0.94, bounding_box=[[0, 15], [10, 15], [10, 25], [0, 25]])
    ]
    ocr_res = OCRResult(raw_text=sample_text, regions=regions)
    extractor = DeclarationExtractor()
    extracted = extractor.extract(ocr_res)

    # Net quantity must be 1 L / 1 Liter, NOT 0.1 m
    assert "1 L" in extracted.net_quantity.value or "1 Liter" in extracted.net_quantity.value or "1000 ml" in extracted.net_quantity.value
    assert extracted.net_quantity.value != "0.1 m"


def test_llm_extractor_fallback_refinement():
    llm_ext = LLMDeclarationExtractor()
    raw_text = "Orange Juice 500 ml\nPacked in Chennai, Tamil Nadu 600001\nMRP ₹40"
    data = ExtractedProductData(
        country_of_origin=ExtractedField(value="Chennai", is_detected=True),
        net_quantity=ExtractedField(value="0.1 m", is_detected=True)
    )
    refined = llm_ext.refine_extracted_data(data, raw_text)

    assert refined.country_of_origin.value == "India"
    assert "500 ml" in refined.net_quantity.value
