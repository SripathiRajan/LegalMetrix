import pytest
from app.ocr.postprocessor import OCRPostProcessor
from app.models.extracted_product import OCRResult, OCRRegion
from app.ocr.preprocessing import ImagePreprocessor
import numpy as np


def test_ocr_postprocessor_character_repair():
    postprocessor = OCRPostProcessor()

    # Test misreads: R5 -> Rs., Pkcl -> Pkd, Ncl -> Net Qty
    raw_text = "ABC Biscuits\nM.R.P. R5 50.0o (incl. of all taxes)\nNcl Qty: 100 gms\nPkcl: 06/2026\nMfg by: ABC Foods Ltd\nCust Care: 1800-111-2222 care@abcfoods.com\nMade in lndia"

    cleaned = postprocessor.clean_text_line(raw_text)

    assert "Rs." in cleaned
    assert "Net Qty" in cleaned
    assert "Pkd:" in cleaned
    assert "Consumer Care" in cleaned
    assert "Made in India" in cleaned
    assert "100 g" in cleaned


def test_ocr_result_postprocessing():
    postprocessor = OCRPostProcessor()

    ocr_res = OCRResult(
        raw_text="MRP R5 100.0o\nNcl Qty: 500 gms",
        regions=[
            OCRRegion(text="MRP R5 100.0o", confidence=0.9, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]]),
            OCRRegion(text="Ncl Qty: 500 gms", confidence=0.9, bounding_box=[[0, 20], [10, 20], [10, 30], [0, 30]])
        ],
        average_confidence=0.9
    )

    processed = postprocessor.process_ocr_result(ocr_res)

    assert "MRP Rs." in processed.regions[0].text
    assert "Net Qty: 500 g" in processed.regions[1].text
    assert "ocr_postprocessed" in processed.preprocessing_applied


def test_image_preprocessor_upscale_and_auto():
    preprocessor = ImagePreprocessor()

    # Create dummy low resolution image
    img = np.full((300, 400, 3), 200, dtype=np.uint8)
    img_bytes = b""
    import cv2
    _, buf = cv2.imencode(".png", img)
    img_bytes = buf.tobytes()

    # Test upscale strategy
    proc_up, orig_up, ops_up, scale_up = preprocessor.preprocess_pipeline(img_bytes, strategy="upscale")
    assert "upscale_1.5x" in ops_up

    # Test auto strategy
    proc_auto, orig_auto, ops_auto, scale_auto = preprocessor.preprocess_pipeline(img_bytes, strategy="auto")
    assert len(ops_auto) > 0
