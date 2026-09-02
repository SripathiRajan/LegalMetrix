import os
import tempfile
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient

from app.vision.frame_selector import FrameSelector, SelectedFrame
from app.models.extracted_product import OCRResult, OCRRegion
from app.services.compliance_service import ComplianceService
from app.ocr.ocr_engine import MockOCREngine
from app.main import app

client = TestClient(app)


def create_synthetic_video(num_frames: int = 20, width: int = 320, height: int = 240) -> str:
    """Helper to generate a temporary test MP4 video with sharp and blurred frames."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_path, fourcc, 10.0, (width, height))

    for i in range(num_frames):
        # Create base image with high contrast text
        frame = np.full((height, width, 3), 240, dtype=np.uint8)
        cv2.putText(frame, f"MRP Rs. 50.00 incl. taxes Frame {i}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(frame, "Net Qty: 500 g", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(frame, "Mfg: SuperFoods Ltd", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        # Apply intentional blur to some frames
        if i % 3 == 0:
            # Heavily blurred frame (low sharpness)
            frame = cv2.GaussianBlur(frame, (21, 21), 0)
        elif i % 2 == 0:
            # Mildly blurred frame
            frame = cv2.GaussianBlur(frame, (7, 7), 0)
        # Otherwise crystal sharp frame

        out.write(frame)

    out.release()
    return temp_path


# 1. Test Frame Sharpness Calculation
def test_frame_sharpness_metric():
    selector = FrameSelector()

    sharp_img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.putText(sharp_img, "CRISP TEXT", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    blurry_img = cv2.GaussianBlur(sharp_img, (15, 15), 0)

    sharp_score = selector.calculate_sharpness(sharp_img)
    blurry_score = selector.calculate_sharpness(blurry_img)

    assert sharp_score > blurry_score
    assert sharp_score > 50.0


# 2. Test Keyframe Extraction from Video
def test_extract_keyframes_from_video():
    selector = FrameSelector()
    video_path = create_synthetic_video(num_frames=20)

    try:
        keyframes = selector.extract_keyframes(video_path, max_frames=3, sample_fps=5.0)

        assert len(keyframes) == 3
        assert all(isinstance(f, SelectedFrame) for f in keyframes)
        assert all(f.sharpness_score > 0 for f in keyframes)
        assert all(f.image_array is not None for f in keyframes)
        # Ensure temporal ordering
        timestamps = [f.timestamp_seconds for f in keyframes]
        assert timestamps == sorted(timestamps)
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


# 3. Test Multi-Frame OCR Merging (Highest Confidence Wins)
def test_merge_multi_frame_ocr_highest_confidence():
    selector = FrameSelector(iou_threshold=0.5)

    # Frame 1: Low confidence or noisy OCR
    frame1_res = OCRResult(
        raw_text="MRP Rs 50\nNet Qty 500g",
        regions=[
            OCRRegion(
                text="MRP Rs 50",
                confidence=0.65,
                bounding_box=[100, 100, 140, 400]
            ),
            OCRRegion(
                text="Net Qty 500g",
                confidence=0.92,
                bounding_box=[200, 100, 240, 400]
            ),
        ],
        average_confidence=0.785
    )

    # Frame 2: Clearer MRP declaration (higher confidence)
    frame2_res = OCRResult(
        raw_text="MRP Rs. 50.00 incl. of all taxes\nNet Qty 500 g",
        regions=[
            OCRRegion(
                text="MRP Rs. 50.00 incl. of all taxes",
                confidence=0.98,
                bounding_box=[102, 101, 141, 402]  # High IoU with Frame 1 MRP
            ),
            OCRRegion(
                text="Net Qty 500 g",
                confidence=0.85,
                bounding_box=[198, 100, 239, 399]  # High IoU with Frame 1 Net Qty
            ),
            OCRRegion(
                text="Mfg: Good Foods Ltd",
                confidence=0.95,
                bounding_box=[300, 100, 340, 500]  # Unique declaration only in Frame 2
            )
        ],
        average_confidence=0.926
    )

    merged = selector.merge_multi_frame_ocr([frame1_res, frame2_res])

    assert len(merged.regions) == 3
    # Check that highest confidence text won for MRP
    mrp_region = next(r for r in merged.regions if "MRP" in r.text)
    assert mrp_region.text == "MRP Rs. 50.00 incl. of all taxes"
    assert mrp_region.confidence == 0.98

    # Check that highest confidence text won for Net Qty (Frame 1 was 0.92 vs Frame 2 was 0.85)
    qty_region = next(r for r in merged.regions if "Net Qty" in r.text)
    assert qty_region.text == "Net Qty 500g"
    assert qty_region.confidence == 0.92

    # Check that unique declaration from Frame 2 is included
    mfg_region = next(r for r in merged.regions if "Mfg" in r.text)
    assert mfg_region.text == "Mfg: Good Foods Ltd"
    assert mfg_region.confidence == 0.95


# 4. Test ComplianceService Video End-to-End Analysis
def test_compliance_service_video_analysis():
    predefined = OCRResult(
        raw_text=(
            "Brand: Royal Foods\n"
            "Generic: Pure Mustard Oil\n"
            "MRP Rs. 150.00 incl. of all taxes\n"
            "Net Quantity: 1 L\n"
            "Mfg Date: 08/2026\n"
            "Manufactured by: Royal Agro Pvt Ltd, Plot 5, Ind Area, Pune - 411001\n"
            "Consumer Care: care@royalfoods.com, 1800-222-333, Pune\n"
            "Country of Origin: India\n"
        ),
        regions=[
            OCRRegion(text="Royal Foods", confidence=0.98, bounding_box=[10, 10, 30, 200]),
            OCRRegion(text="Pure Mustard Oil", confidence=0.98, bounding_box=[40, 10, 60, 200]),
            OCRRegion(text="MRP Rs. 150.00 incl. of all taxes", confidence=0.98, bounding_box=[70, 10, 90, 300]),
            OCRRegion(text="Net Quantity: 1 L", confidence=0.98, bounding_box=[100, 10, 120, 200]),
            OCRRegion(text="Mfg Date: 08/2026", confidence=0.98, bounding_box=[130, 10, 150, 200]),
            OCRRegion(text="Manufactured by: Royal Agro Pvt Ltd, Plot 5, Ind Area, Pune - 411001", confidence=0.98, bounding_box=[160, 10, 180, 500]),
            OCRRegion(text="Consumer Care: care@royalfoods.com, 1800-222-333, Pune", confidence=0.98, bounding_box=[190, 10, 210, 400]),
            OCRRegion(text="Country of Origin: India", confidence=0.98, bounding_box=[220, 10, 240, 200]),
        ],
        average_confidence=0.98
    )
    mock_ocr = MockOCREngine(predefined_result=predefined)


    service = ComplianceService(ocr_engine=mock_ocr)
    video_path = create_synthetic_video(num_frames=10)

    try:
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        response = service.analyze_video_end_to_end(
            video_bytes=video_bytes,
            max_frames=3,
            persist=False
        )

        assert response.compliance_result is not None
        assert response.compliance_result.overall_status == "COMPLIANT"
        assert len(response.selected_frames) > 0
        assert response.ocr_summary["multi_frame_fusion"] is True
        assert response.annotated_image is not None
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


# 5. Test POST /api/analyze/video FastAPI Endpoint
def test_api_analyze_video_endpoint():
    video_path = create_synthetic_video(num_frames=10)

    try:
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        files = {"file": ("inspection_stream.mp4", video_bytes, "video/mp4")}
        response = client.post("/api/analyze/video?max_frames=3", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "compliance_result" in data
        assert "selected_frames" in data
        assert len(data["selected_frames"]) > 0
        assert "ocr_summary" in data
        assert data["ocr_summary"]["multi_frame_fusion"] is True
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
