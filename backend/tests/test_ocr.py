import io
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient

from app.main import app
from app.ocr.preprocessing import ImagePreprocessor
from app.ocr.ocr_engine import MockOCREngine
from app.models.extracted_product import OCRResult, OCRRegion
from app.services.compliance_service import ComplianceService
from app.models.product import OverallComplianceStatus

client = TestClient(app)


def create_dummy_image_bytes(width=400, height=200, color=(255, 255, 255), text="TEST IMAGE"):
    """Creates a synthetic test image using OpenCV in PNG format."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    cv2.putText(img, text, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    success, buffer = cv2.imencode(".png", img)
    assert success
    return buffer.tobytes()


# 1. Test image preprocessing pipeline with multiple strategies
def test_image_preprocessing_strategies():
    preprocessor = ImagePreprocessor()
    img_bytes = create_dummy_image_bytes(800, 600)

    # Standard
    proc_std, orig_std, ops_std, scale_std = preprocessor.preprocess_pipeline(img_bytes, strategy="standard")
    assert len(proc_std.shape) == 2  # Grayscale
    assert orig_std is not None
    assert "grayscale" in ops_std

    # Denoise
    proc_dn, orig_dn, ops_dn, scale_dn = preprocessor.preprocess_pipeline(img_bytes, strategy="denoise")
    assert "median_denoise" in ops_dn

    # High Contrast
    proc_hc, orig_hc, ops_hc, scale_hc = preprocessor.preprocess_pipeline(img_bytes, strategy="high_contrast")
    assert "sharpen" in ops_hc

    # Binary Threshold
    proc_bin, orig_bin, ops_bin, scale_bin = preprocessor.preprocess_pipeline(img_bytes, strategy="binary")
    assert "adaptive_threshold_binary" in ops_bin

    # Raw
    proc_raw, orig_raw, ops_raw, scale_raw = preprocessor.preprocess_pipeline(img_bytes, strategy="raw")
    assert len(proc_raw.shape) == 3  # Color kept


# 2. Test Invalid/Corrupted Image handling
def test_invalid_image_handling():
    invalid_bytes = b"NOT_AN_IMAGE_CONTENT_CORRUPTED"

    resp = client.post(
        "/api/ocr/extract",
        files={"file": ("corrupt.png", io.BytesIO(invalid_bytes), "image/png")}
    )
    assert resp.status_code == 400
    assert "Invalid image format" in resp.json()["detail"]


# 3. Test Non-image file type rejection
def test_non_image_content_type():
    resp = client.post(
        "/api/ocr/extract",
        files={"file": ("test.txt", io.BytesIO(b"hello text"), "text/plain")}
    )
    assert resp.status_code == 400
    assert "Invalid file type" in resp.json()["detail"]


# 4. Test POST /api/ocr/extract endpoint with Mocked OCR
def test_api_ocr_extract_endpoint(monkeypatch):
    mock_ocr = MockOCREngine(OCRResult(
        raw_text="ABC Biscuits\nMRP Rs. 50 (incl. of all taxes)\nNet Qty: 100 g\nPkd: 06/2026\nMfg by: ABC Foods, Chennai, Tamil Nadu 600001\nConsumer Care: 1800-111-2222 care@abcfoods.in\nCountry of Origin: India",
        regions=[
            OCRRegion(text="ABC Biscuits", confidence=0.98, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]]),
            OCRRegion(text="MRP Rs. 50 (incl. of all taxes)", confidence=0.95, bounding_box=[[0, 20], [10, 20], [10, 30], [0, 30]]),
            OCRRegion(text="Net Qty: 100 g", confidence=0.97, bounding_box=[[0, 40], [10, 40], [10, 50], [0, 50]]),
            OCRRegion(text="Pkd: 06/2026", confidence=0.94, bounding_box=[[0, 60], [10, 60], [10, 70], [0, 70]]),
            OCRRegion(text="Mfg by: ABC Foods, Chennai, Tamil Nadu 600001", confidence=0.96, bounding_box=[[0, 80], [10, 80], [10, 90], [0, 90]]),
            OCRRegion(text="Consumer Care: 1800-111-2222 care@abcfoods.in", confidence=0.97, bounding_box=[[0, 100], [10, 100], [10, 110], [0, 110]]),
            OCRRegion(text="Country of Origin: India", confidence=0.99, bounding_box=[[0, 120], [10, 120], [10, 130], [0, 130]])
        ],
        average_confidence=0.965
    ))

    from app import main
    monkeypatch.setattr(main.compliance_service, "ocr_engine", mock_ocr)

    img_bytes = create_dummy_image_bytes()
    resp = client.post(
        "/api/ocr/extract",
        files={"file": ("label.png", io.BytesIO(img_bytes), "image/png")}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "ABC Biscuits" in data["ocr_text"]
    assert data["fields"]["mrp"]["is_detected"]
    assert "₹50" in data["fields"]["mrp"]["value"]
    assert data["fields"]["net_quantity"]["value"] == "100 g"
    assert data["fields"]["country_of_origin"]["value"] == "India"


# 5. Test POST /api/analyze End-to-End endpoint
def test_api_analyze_end_to_end(monkeypatch):
    mock_ocr = MockOCREngine(OCRResult(
        raw_text="Healthy Oats\nMRP ₹120.00 incl. of all taxes\nNet Wt: 500 g\nMfd: 04/2026\nManufactured by: Oats India Ltd, Jaipur, Rajasthan 302001\nCustomer Care: 1800-333-4444 help@oatsindia.com\nMade in India",
        regions=[
            OCRRegion(text="Healthy Oats", confidence=0.98, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]]),
            OCRRegion(text="MRP ₹120.00 incl. of all taxes", confidence=0.96, bounding_box=[[0, 20], [10, 20], [10, 30], [0, 30]]),
            OCRRegion(text="Net Wt: 500 g", confidence=0.97, bounding_box=[[0, 40], [10, 40], [10, 50], [0, 50]]),
            OCRRegion(text="Mfd: 04/2026", confidence=0.95, bounding_box=[[0, 60], [10, 60], [10, 70], [0, 70]]),
            OCRRegion(text="Manufactured by: Oats India Ltd, Jaipur, Rajasthan 302001", confidence=0.95, bounding_box=[[0, 80], [10, 80], [10, 90], [0, 90]]),
            OCRRegion(text="Customer Care: 1800-333-4444 help@oatsindia.com", confidence=0.96, bounding_box=[[0, 100], [10, 100], [10, 110], [0, 110]]),
            OCRRegion(text="Made in India", confidence=0.98, bounding_box=[[0, 120], [10, 120], [10, 130], [0, 130]])
        ],
        average_confidence=0.964
    ))

    from app import main
    monkeypatch.setattr(main.compliance_service, "ocr_engine", mock_ocr)

    img_bytes = create_dummy_image_bytes()
    resp = client.post(
        "/api/analyze",
        files={"file": ("oats.png", io.BytesIO(img_bytes), "image/png")}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "extracted_data" in data
    assert "compliance_result" in data
    assert data["compliance_result"]["overall_status"] == OverallComplianceStatus.COMPLIANT
    assert data["compliance_result"]["compliance_score"] == 100.0
    assert data["compliance_result"]["failed"] == 0


# 6. Test POST /api/ocr/extract endpoint with use_ensemble=true
def test_api_ocr_extract_with_ensemble(monkeypatch):
    mock_ocr = MockOCREngine(OCRResult(
        raw_text="ABC Biscuits\nMRP Rs. 50 (incl. of all taxes)\nNet Qty: 100 g\nCountry of Origin: India",
        regions=[
            OCRRegion(text="ABC Biscuits", confidence=0.98, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]]),
            OCRRegion(text="MRP Rs. 50 (incl. of all taxes)", confidence=0.95, bounding_box=[[0, 20], [10, 20], [10, 30], [0, 30]]),
            OCRRegion(text="Net Qty: 100 g", confidence=0.97, bounding_box=[[0, 40], [10, 40], [10, 50], [0, 50]]),
            OCRRegion(text="Country of Origin: India", confidence=0.99, bounding_box=[[0, 120], [10, 120], [10, 130], [0, 130]])
        ],
        average_confidence=0.97
    ))

    from app import main
    monkeypatch.setattr(main.compliance_service, "ocr_engine", mock_ocr)

    img_bytes = create_dummy_image_bytes()
    resp = client.post(
        "/api/ocr/extract?use_ensemble=true",
        files={"file": ("label.png", io.BytesIO(img_bytes), "image/png")}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "ABC Biscuits" in data["ocr_text"]
    assert data["fields"]["mrp"]["is_detected"]
    assert data["fields"]["country_of_origin"]["value"] == "India"


# 7. Test POST /api/analyze endpoint with use_ensemble=true
def test_api_analyze_with_ensemble(monkeypatch):
    mock_ocr = MockOCREngine(OCRResult(
        raw_text="Healthy Oats\nMRP ₹120.00 incl. of all taxes\nNet Wt: 500 g\nMfd: 04/2026\nManufactured by: Oats India Ltd, Jaipur, Rajasthan 302001\nCustomer Care: 1800-333-4444 help@oatsindia.com\nMade in India",
        regions=[
            OCRRegion(text="Healthy Oats", confidence=0.98, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]]),
            OCRRegion(text="MRP ₹120.00 incl. of all taxes", confidence=0.96, bounding_box=[[0, 20], [10, 20], [10, 30], [0, 30]]),
            OCRRegion(text="Net Wt: 500 g", confidence=0.97, bounding_box=[[0, 40], [10, 40], [10, 50], [0, 50]]),
            OCRRegion(text="Mfd: 04/2026", confidence=0.95, bounding_box=[[0, 60], [10, 60], [10, 70], [0, 70]]),
            OCRRegion(text="Manufactured by: Oats India Ltd, Jaipur, Rajasthan 302001", confidence=0.95, bounding_box=[[0, 80], [10, 80], [10, 90], [0, 90]]),
            OCRRegion(text="Customer Care: 1800-333-4444 help@oatsindia.com", confidence=0.96, bounding_box=[[0, 100], [10, 100], [10, 110], [0, 110]]),
            OCRRegion(text="Made in India", confidence=0.98, bounding_box=[[0, 120], [10, 120], [10, 130], [0, 130]])
        ],
        average_confidence=0.964
    ))

    from app import main
    monkeypatch.setattr(main.compliance_service, "ocr_engine", mock_ocr)

    img_bytes = create_dummy_image_bytes()
    resp = client.post(
        "/api/analyze?use_ensemble=true&multi_pass=false",
        files={"file": ("oats.png", io.BytesIO(img_bytes), "image/png")}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "extracted_data" in data
    assert "compliance_result" in data
    assert data["compliance_result"]["overall_status"] == OverallComplianceStatus.COMPLIANT
    assert data["compliance_result"]["compliance_score"] == 100.0

