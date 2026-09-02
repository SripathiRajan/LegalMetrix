import pytest
import numpy as np

from app.models.extracted_product import OCRResult, OCRRegion
from app.ocr.ocr_engine import (
    BaseOCREngine,
    MockOCREngine,
    EasyOCREngine,
    TesseractOCREngine
)
from app.ocr.ensemble import OCREnsemble, EnsembleResult
from app.vision.bbox_utils import BBoxUtils


# Helper fixture creating dummy numpy image
@pytest.fixture
def dummy_image():
    return np.zeros((300, 500, 3), dtype=np.uint8)


# 1. Test Case 1: Full Agreement Across Multiple Engines
def test_ensemble_full_agreement(dummy_image):
    # Engine 1 (e.g., standard extractions)
    engine1_res = OCRResult(
        raw_text="ABC Biscuits\nMRP ₹50.00 incl. of all taxes\nNet Qty: 100 g\nPkd: 06/2026\nManufactured by: ABC Foods Ltd, Madurai, Tamil Nadu 625001\nConsumer Care: 1800-123-4567 care@abcfoods.com\nCountry of Origin: India",
        regions=[
            OCRRegion(text="ABC Biscuits", confidence=0.92, bounding_box=[[10, 10], [200, 10], [200, 40], [10, 40]]),
            OCRRegion(text="MRP ₹50.00 incl. of all taxes", confidence=0.95, bounding_box=[[10, 50], [300, 50], [300, 80], [10, 80]]),
            OCRRegion(text="Net Qty: 100 g", confidence=0.94, bounding_box=[[10, 90], [150, 90], [150, 120], [10, 120]]),
            OCRRegion(text="Pkd: 06/2026", confidence=0.93, bounding_box=[[10, 130], [140, 130], [140, 160], [10, 160]]),
            OCRRegion(text="Manufactured by: ABC Foods Ltd, Madurai, Tamil Nadu 625001", confidence=0.91, bounding_box=[[10, 170], [450, 170], [450, 200], [10, 200]]),
            OCRRegion(text="Consumer Care: 1800-123-4567 care@abcfoods.com", confidence=0.92, bounding_box=[[10, 210], [400, 210], [400, 240], [10, 240]]),
            OCRRegion(text="Country of Origin: India", confidence=0.95, bounding_box=[[10, 250], [250, 250], [250, 280], [10, 280]])
        ],
        average_confidence=0.931
    )

    # Engine 2 (e.g., slightly higher confidence on some fields with overlapping bboxes)
    engine2_res = OCRResult(
        raw_text="ABC Biscuits\nMRP ₹50.00 incl. of all taxes\nNet Qty: 100 g\nPkd: 06/2026\nManufactured by: ABC Foods Ltd, Madurai, Tamil Nadu 625001\nConsumer Care: 1800-123-4567 care@abcfoods.com\nCountry of Origin: India",
        regions=[
            OCRRegion(text="ABC Biscuits", confidence=0.98, bounding_box=[[11, 10], [199, 10], [199, 41], [11, 41]]),
            OCRRegion(text="MRP ₹50.00 incl. of all taxes", confidence=0.99, bounding_box=[[10, 51], [300, 51], [300, 80], [10, 80]]),
            OCRRegion(text="Net Qty: 100 g", confidence=0.98, bounding_box=[[10, 90], [152, 90], [152, 120], [10, 120]]),
            OCRRegion(text="Pkd: 06/2026", confidence=0.97, bounding_box=[[10, 130], [140, 130], [140, 160], [10, 160]]),
            OCRRegion(text="Manufactured by: ABC Foods Ltd, Madurai, Tamil Nadu 625001", confidence=0.96, bounding_box=[[10, 170], [450, 170], [450, 200], [10, 200]]),
            OCRRegion(text="Consumer Care: 1800-123-4567 care@abcfoods.com", confidence=0.97, bounding_box=[[10, 210], [400, 210], [400, 240], [10, 240]]),
            OCRRegion(text="Country of Origin: India", confidence=0.99, bounding_box=[[10, 250], [250, 250], [250, 280], [10, 280]])
        ],
        average_confidence=0.977
    )

    mock_engine1 = MockOCREngine(engine1_res)
    mock_engine2 = MockOCREngine(engine2_res)

    ensemble = OCREnsemble(engines=[mock_engine1, mock_engine2], iou_threshold=0.5)
    result = ensemble.process(dummy_image)

    assert isinstance(result, EnsembleResult)
    assert result.winning_engine == "MockOCREngine_1"  # Higher confidence engine wins
    assert result.engine_agreement_score == 1.0  # 100% agreement on all 7 detected regions
    assert len(result.merged_result.regions) == 7
    assert result.merged_result.average_confidence >= 0.97  # Higher confidences won

    # Verify winning text per matched region has highest confidence
    mrp_region = [r for r in result.merged_result.regions if "MRP" in r.text][0]
    assert mrp_region.confidence == 0.99
    assert result.metadata["clusters_count"] == 7
    assert result.metadata["agreed_clusters_count"] == 7


# 2. Test Case 2: Partial Disagreement Across Engines (Conflicting text & unique regions)
def test_ensemble_partial_disagreement(dummy_image):
    # Engine 1 extracts MRP with lower confidence and misses date, but finds a unique subtitle
    engine1_res = OCRResult(
        raw_text="ABC Biscuits\nCrispy Treat\nMRP Rs 50\nNet Qty: 100 g",
        regions=[
            OCRRegion(text="ABC Biscuits", confidence=0.95, bounding_box=[[10, 10], [200, 10], [200, 40], [10, 40]]),
            OCRRegion(text="Crispy Treat", confidence=0.90, bounding_box=[[10, 45], [150, 45], [150, 65], [10, 65]]),  # Unique to Engine 1
            OCRRegion(text="MRP Rs 50", confidence=0.80, bounding_box=[[10, 70], [200, 70], [200, 100], [10, 100]]),
            OCRRegion(text="Net Qty: 100 g", confidence=0.92, bounding_box=[[10, 110], [180, 110], [180, 140], [10, 140]])
        ],
        average_confidence=0.892
    )

    # Engine 2 extracts complete statutory declaration with higher MRP confidence and adds Pkd date
    engine2_res = OCRResult(
        raw_text="ABC Biscuits\nMRP ₹50.00 incl. of all taxes\nNet Qty: 100 g\nPkd: 06/2026\nCountry of Origin: India",
        regions=[
            OCRRegion(text="ABC Biscuits", confidence=0.98, bounding_box=[[12, 10], [202, 10], [202, 40], [12, 40]]),
            OCRRegion(text="MRP ₹50.00 incl. of all taxes", confidence=0.98, bounding_box=[[10, 72], [200, 72], [200, 99], [10, 99]]),
            OCRRegion(text="Net Qty: 100 g", confidence=0.96, bounding_box=[[10, 110], [180, 110], [180, 140], [10, 140]]),
            OCRRegion(text="Pkd: 06/2026", confidence=0.94, bounding_box=[[10, 150], [140, 150], [140, 180], [10, 180]]),  # Unique to Engine 2
            OCRRegion(text="Country of Origin: India", confidence=0.97, bounding_box=[[10, 190], [250, 190], [250, 220], [10, 220]])  # Unique to Engine 2
        ],
        average_confidence=0.966
    )

    mock_engine1 = MockOCREngine(engine1_res)
    mock_engine2 = MockOCREngine(engine2_res)

    ensemble = OCREnsemble(engines=[mock_engine1, mock_engine2], iou_threshold=0.5)
    result = ensemble.process(dummy_image)

    assert isinstance(result, EnsembleResult)
    # Primary result should be Engine 2 (due to statutory keyword & pattern scoring)
    assert result.winning_engine == "MockOCREngine_1"
    assert "MRP ₹50.00" in result.primary_result.raw_text

    # Merged result should contain both unique regions ("Crispy Treat" and "Pkd: 06/2026")
    merged_texts = [r.text for r in result.merged_result.regions]
    assert "Crispy Treat" in merged_texts
    assert "Pkd: 06/2026" in merged_texts
    assert "MRP ₹50.00 incl. of all taxes" in merged_texts

    # Check highest confidence won for the matched MRP region
    mrp_merged = [r for r in result.merged_result.regions if "MRP" in r.text][0]
    assert mrp_merged.confidence == 0.98
    assert mrp_merged.text == "MRP ₹50.00 incl. of all taxes"

    # Agreement score should be between 0.0 and 1.0 (some agreed clusters, some unique)
    assert 0.0 < result.engine_agreement_score < 1.0
    assert result.metadata["agreed_clusters_count"] == 3  # ABC Biscuits, MRP, Net Qty
    assert result.metadata["clusters_count"] == 6  # 3 shared + 1 from Eng1 + 2 from Eng2


# 3. Test Case 3: One Engine Empty / Uninitialized Fallback
def test_ensemble_one_empty_engine(dummy_image):
    # Engine 1 returns valid extraction
    valid_res = OCRResult(
        raw_text="Pure Honey\nMRP: Rs. 250.00\nNet Content: 500 g\nCountry of Origin: India",
        regions=[
            OCRRegion(text="Pure Honey", confidence=0.95, bounding_box=[[10, 10], [150, 10], [150, 40], [10, 40]]),
            OCRRegion(text="MRP: Rs. 250.00", confidence=0.93, bounding_box=[[10, 50], [200, 50], [200, 80], [10, 80]]),
            OCRRegion(text="Net Content: 500 g", confidence=0.94, bounding_box=[[10, 90], [180, 90], [180, 120], [10, 120]]),
            OCRRegion(text="Country of Origin: India", confidence=0.97, bounding_box=[[10, 130], [240, 130], [240, 160], [10, 160]])
        ],
        average_confidence=0.948
    )

    # Engine 2 is empty (e.g. uninitialized weights or failed detection)
    empty_res = OCRResult(
        raw_text="",
        regions=[],
        average_confidence=0.0
    )

    mock_valid = MockOCREngine(valid_res)
    mock_empty = MockOCREngine(empty_res)

    ensemble = OCREnsemble(engines=[mock_valid, mock_empty])
    result = ensemble.process(dummy_image)

    assert isinstance(result, EnsembleResult)
    assert result.winning_engine == "MockOCREngine_0"
    assert result.engine_agreement_score == 1.0  # Only 1 active engine evaluated
    assert "Pure Honey" in result.primary_result.raw_text
    assert len(result.merged_result.regions) == 4
    assert result.metadata["active_engines_count"] == 1


# 4. Test Case 4: All Engines Empty
def test_ensemble_all_engines_empty(dummy_image):
    mock_empty1 = MockOCREngine(OCRResult(raw_text="", regions=[], average_confidence=0.0))
    mock_empty2 = MockOCREngine(OCRResult(raw_text="", regions=[], average_confidence=0.0))

    ensemble = OCREnsemble(engines=[mock_empty1, mock_empty2])
    result = ensemble.process(dummy_image)

    assert result.winning_engine == "None"
    assert result.engine_agreement_score == 0.0
    assert result.primary_result.raw_text == ""
    assert len(result.merged_result.regions) == 0


# 5. Test Case 5: Lazy Engine Initializers and Fallback Mode
def test_lazy_engines_fallback(dummy_image):
    easy_engine = EasyOCREngine()
    tess_engine = TesseractOCREngine()

    # When optional libraries or weights are not installed in the environment,
    # the engines must safely return an empty OCRResult rather than raising unhandled errors
    easy_res = easy_engine.extract_text(dummy_image)
    tess_res = tess_engine.extract_text(dummy_image)

    assert isinstance(easy_res, OCRResult)
    assert isinstance(tess_res, OCRResult)


# 6. Test Case 6: BBoxUtils IoU Calculation
def test_bbox_utils_iou():
    box1 = [0, 0, 10, 10]
    box2 = [0, 0, 10, 10]
    assert BBoxUtils.calculate_iou(box1, box2) == 1.0

    # Non-overlapping
    box3 = [20, 20, 30, 30]
    assert BBoxUtils.calculate_iou(box1, box3) == 0.0

    # 50% overlap horizontally: [0,0,10,10] and [5,0,15,10]
    # intersection: [5,0,10,10] -> area 50
    # union: 100 + 100 - 50 = 150 -> IoU = 50/150 = 0.3333
    box4 = [5, 0, 15, 10]
    assert abs(BBoxUtils.calculate_iou(box1, box4) - (50.0 / 150.0)) < 0.001

    # 4-point polygon format
    poly1 = [[0, 0], [10, 0], [10, 10], [0, 10]]
    poly2 = [[0, 0], [10, 0], [10, 10], [0, 10]]
    assert BBoxUtils.calculate_iou(poly1, poly2) == 1.0
