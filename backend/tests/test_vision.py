import io
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient

from app.main import app
from app.vision.bbox_utils import BBoxUtils
from app.vision.readability import ReadabilityAnalyzer, ReadabilityConfig, ReadabilityStatus
from app.vision.spatial_analysis import SpatialAnalysis
from app.vision.evidence import VisualEvidence, EvidenceManager, EvidenceAnnotator
from app.models.extracted_product import OCRResult, OCRRegion, ExtractedField, ExtractedProductData
from app.ocr.ocr_engine import MockOCREngine
from app.models.product import OverallComplianceStatus

client = TestClient(app)


def create_synthetic_image(width=800, height=600):
    img = np.full((height, width, 3), (255, 255, 255), dtype=np.uint8)
    cv2.putText(img, "TEST LABEL", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    success, buffer = cv2.imencode(".png", img)
    assert success
    return img, buffer.tobytes()


# 1. Test BBox Utilities (to_xyxy, validate, dimensions, area, normalization, scale, merge)
def test_bbox_utils_comprehensive():
    # Polygon format to xyxy
    poly_box = [[10.0, 20.0], [100.0, 20.0], [100.0, 50.0], [10.0, 50.0]]
    xyxy = BBoxUtils.to_xyxy(poly_box)
    assert xyxy == [10.0, 20.0, 100.0, 50.0]

    # Validate bbox
    assert BBoxUtils.validate_bbox(xyxy, img_width=800, img_height=600)
    assert not BBoxUtils.validate_bbox([100.0, 50.0, 10.0, 20.0], 800, 600)  # Inverted
    assert not BBoxUtils.validate_bbox([-10.0, 20.0, 100.0, 50.0], 800, 600) # Out of bounds

    # Dimensions and Area
    w, h = BBoxUtils.get_dimensions(xyxy)
    assert w == 90.0
    assert h == 30.0
    assert BBoxUtils.get_area(xyxy) == 2700.0

    # Center
    cx, cy = BBoxUtils.get_center(xyxy)
    assert cx == 55.0
    assert cy == 35.0

    # Normalization (relative to 800x600)
    norm = BBoxUtils.normalize_bbox(xyxy, 800, 600)
    assert norm == [0.0125, 0.0333, 0.125, 0.0833]

    # Scale to original
    scaled = BBoxUtils.scale_bbox_to_original(xyxy, scale_factor=0.5)
    assert scaled == [20.0, 40.0, 200.0, 100.0]

    # Merge bboxes
    b1 = [10.0, 10.0, 50.0, 50.0]
    b2 = [40.0, 30.0, 120.0, 80.0]
    merged = BBoxUtils.merge_bboxes([b1, b2])
    assert merged == [10.0, 10.0, 120.0, 80.0]


# 2. Test Spatial Placement Classification
def test_spatial_analysis_classification():
    # Top Left
    pos_tl = SpatialAnalysis.classify_position([50, 50, 150, 100], img_width=1000, img_height=1000)
    assert pos_tl["horizontal"] == "LEFT"
    assert pos_tl["vertical"] == "TOP"
    assert pos_tl["quadrant"] == "TOP_LEFT"

    # Bottom Right
    pos_br = SpatialAnalysis.classify_position([800, 800, 950, 950], img_width=1000, img_height=1000)
    assert pos_br["horizontal"] == "RIGHT"
    assert pos_br["vertical"] == "BOTTOM"
    assert pos_br["quadrant"] == "BOTTOM_RIGHT"

    # Center Middle
    pos_mid = SpatialAnalysis.classify_position([450, 450, 550, 550], img_width=1000, img_height=1000)
    assert pos_mid["horizontal"] == "CENTER"
    assert pos_mid["vertical"] == "MIDDLE"


# 3. Test Readability Analyzer (Readable, Low, Unreadable, Human Verification)
def test_readability_analyzer():
    analyzer = ReadabilityAnalyzer()

    # Clear, high confidence, large text -> READABLE
    res_readable = analyzer.analyze_readability(
        confidence=0.96,
        bbox=[100, 100, 300, 140],  # 40px height
        img_width=1920,
        img_height=1080
    )
    assert res_readable["status"] == ReadabilityStatus.READABLE
    assert res_readable["text_height_pixels"] == 40.0

    # Very low confidence -> UNREADABLE
    res_unreadable = analyzer.analyze_readability(
        confidence=0.35,
        bbox=[100, 100, 300, 140],
        img_width=1920,
        img_height=1080
    )
    assert res_unreadable["status"] == ReadabilityStatus.UNREADABLE

    # Very small text (< 8px) -> UNREADABLE
    res_small = analyzer.analyze_readability(
        confidence=0.95,
        bbox=[100, 100, 200, 106],  # 6px height
        img_width=1920,
        img_height=1080
    )
    assert res_small["status"] == ReadabilityStatus.UNREADABLE

    # Medium confidence / borderline text -> REQUIRES_HUMAN_VERIFICATION / LOW_READABILITY
    res_borderline = analyzer.analyze_readability(
        confidence=0.66,
        bbox=[100, 100, 200, 110],  # 10px height
        img_width=1920,
        img_height=1080
    )
    assert res_borderline["status"] in [ReadabilityStatus.REQUIRES_HUMAN_VERIFICATION, ReadabilityStatus.LOW_READABILITY]


# 4. Test Evidence Linking and Missing Declaration Evidence
def test_evidence_manager_linking():
    manager = EvidenceManager()

    # Field with detected bounding boxes
    boxes = [[[10.0, 20.0], [200.0, 20.0], [200.0, 60.0], [10.0, 60.0]]]
    ev_detected = manager.build_evidence(
        bounding_boxes=boxes,
        confidence=0.95,
        source_text="MRP ₹50.00 incl. of all taxes",
        img_width=1920,
        img_height=1080
    )
    assert ev_detected.has_evidence
    assert ev_detected.text_height_pixels == 40.0
    assert ev_detected.readability_status == ReadabilityStatus.READABLE
    assert len(ev_detected.normalized_bbox) == 4

    # Missing declaration (no bounding boxes)
    ev_missing = manager.build_evidence(
        bounding_boxes=[],
        confidence=0.0,
        source_text=None,
        img_width=1920,
        img_height=1080
    )
    assert not ev_missing.has_evidence
    assert ev_missing.bounding_box == []
    assert ev_missing.readability_status == ReadabilityStatus.UNREADABLE


# 5. Test Annotated Image Generation
def test_evidence_annotator():
    img, _ = create_synthetic_image(800, 600)
    annotations = [
        {"bounding_box": [50, 50, 300, 100], "label": "MRP", "status": "PASS"},
        {"bounding_box": [50, 150, 250, 190], "label": "NET QTY", "status": "PASS"},
        {"bounding_box": [50, 250, 400, 300], "label": "MANUFACTURER", "status": "WARNING"}
    ]

    annotated_array, b64_str = EvidenceAnnotator.annotate_image(img, annotations)
    assert annotated_array is not None
    assert b64_str.startswith("data:image/png;base64,")
    assert len(b64_str) > 50


# 6. Test POST /api/vision/analyze endpoint
def test_api_vision_analyze_endpoint(monkeypatch):
    mock_ocr = MockOCREngine(OCRResult(
        raw_text="ABC Biscuits\nMRP ₹50.00 incl. of all taxes\nNet Qty: 100 g\nPkd: 06/2026\nMfg by: ABC Foods Ltd, Chennai, Tamil Nadu 600001\nConsumer Care: 1800-111-2222 care@abcfoods.in\nCountry of Origin: India",
        regions=[
            OCRRegion(text="ABC Biscuits", confidence=0.98, bounding_box=[[50, 50], [250, 50], [250, 90], [50, 90]]),
            OCRRegion(text="MRP ₹50.00 incl. of all taxes", confidence=0.95, bounding_box=[[50, 110], [350, 110], [350, 150], [50, 150]]),
            OCRRegion(text="Net Qty: 100 g", confidence=0.97, bounding_box=[[50, 170], [200, 170], [200, 210], [50, 210]]),
            OCRRegion(text="Pkd: 06/2026", confidence=0.94, bounding_box=[[50, 230], [200, 230], [200, 270], [50, 270]]),
            OCRRegion(text="Mfg by: ABC Foods Ltd, Chennai, Tamil Nadu 600001", confidence=0.96, bounding_box=[[50, 290], [550, 290], [550, 330], [50, 330]]),
            OCRRegion(text="Consumer Care: 1800-111-2222 care@abcfoods.in", confidence=0.97, bounding_box=[[50, 350], [500, 350], [500, 390], [50, 390]]),
            OCRRegion(text="Country of Origin: India", confidence=0.99, bounding_box=[[50, 410], [300, 410], [300, 450], [50, 450]])
        ],
        average_confidence=0.965
    ))

    from app import main
    monkeypatch.setattr(main.compliance_service, "ocr_engine", mock_ocr)

    _, img_bytes = create_synthetic_image(800, 600)
    resp = client.post(
        "/api/vision/analyze",
        files={"file": ("label.png", io.BytesIO(img_bytes), "image/png")}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["image_width"] == 800
    assert data["image_height"] == 600
    assert data["regions_detected"] == 7
    assert "mrp" in data["fields_with_evidence"]
    mrp_field = data["fields_with_evidence"]["mrp"]
    assert mrp_field["evidence"] is not None
    assert mrp_field["evidence"]["text_height_pixels"] == 40.0
    assert mrp_field["evidence"]["readability_status"] == "READABLE"
    assert data["annotated_image"].startswith("data:image/png;base64,")


# 7. Test End-to-End Image Analysis with Visual Evidence in Compliance Results
def test_end_to_end_compliance_with_evidence(monkeypatch):
    mock_ocr = MockOCREngine(OCRResult(
        raw_text="Healthy Oats\nMRP ₹120.00 incl. of all taxes\nNet Wt: 500 g\nMfd: 04/2026\nManufactured by: Oats India Ltd, Jaipur, Rajasthan 302001\nCustomer Care: 1800-333-4444 help@oatsindia.com\nMade in India",
        regions=[
            OCRRegion(text="Healthy Oats", confidence=0.98, bounding_box=[[20, 20], [200, 20], [200, 60], [20, 60]]),
            OCRRegion(text="MRP ₹120.00 incl. of all taxes", confidence=0.96, bounding_box=[[20, 80], [300, 80], [300, 120], [20, 120]]),
            OCRRegion(text="Net Wt: 500 g", confidence=0.97, bounding_box=[[20, 140], [180, 140], [180, 180], [20, 180]]),
            OCRRegion(text="Mfd: 04/2026", confidence=0.95, bounding_box=[[20, 200], [180, 200], [180, 240], [20, 240]]),
            OCRRegion(text="Manufactured by: Oats India Ltd, Jaipur, Rajasthan 302001", confidence=0.95, bounding_box=[[20, 260], [500, 260], [500, 300], [20, 300]]),
            OCRRegion(text="Customer Care: 1800-333-4444 help@oatsindia.com", confidence=0.96, bounding_box=[[20, 320], [450, 320], [450, 360], [20, 360]]),
            OCRRegion(text="Made in India", confidence=0.98, bounding_box=[[20, 380], [200, 380], [200, 420], [20, 420]])
        ],
        average_confidence=0.964
    ))

    from app import main
    monkeypatch.setattr(main.compliance_service, "ocr_engine", mock_ocr)

    _, img_bytes = create_synthetic_image(800, 600)
    resp = client.post(
        "/api/analyze",
        files={"file": ("oats.png", io.BytesIO(img_bytes), "image/png")}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["compliance_result"]["overall_status"] == OverallComplianceStatus.COMPLIANT
    assert data["annotated_image"] is not None

    # Check that individual rule check results contain visual evidence
    mrp_rule = next(r for r in data["compliance_result"]["results"] if r["rule_id"] == "LMPC_RULE_6_1_E")
    assert mrp_rule["status"] == "PASS"
    assert mrp_rule["evidence"] is not None
    assert mrp_rule["evidence"]["has_evidence"] is True
    assert mrp_rule["evidence"]["readability_status"] == "READABLE"
    assert len(mrp_rule["evidence"]["bounding_boxes"]) > 0
