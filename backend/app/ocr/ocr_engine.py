import logging
from abc import ABC, abstractmethod
from typing import List, Any, Optional
import numpy as np

from app.models.extracted_product import OCRResult, OCRRegion
from app.ocr.preprocessing import ImagePreprocessor

logger = logging.getLogger(__name__)


class BaseOCREngine(ABC):
    """
    Abstract interface for OCR engines to ensure pluggability.
    Allows easy swapping between PaddleOCR, Tesseract, EasyOCR, or Cloud OCR.
    """

    @abstractmethod
    def extract_text(self, image: Any) -> OCRResult:
        """
        Takes preprocessed image array (numpy array) and returns structured OCRResult.
        """
        pass


class PaddleOCREngine(BaseOCREngine):
    """
    PaddleOCR implementation for multilingual, high-accuracy text and bounding box detection.
    """

    def __init__(self, lang: str = "en", use_angle_cls: bool = True):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.ocr_instance = None
        self._initialize_engine()

    def _initialize_engine(self):
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR engine...")
            self.ocr_instance = PaddleOCR(use_angle_cls=self.use_angle_cls, lang=self.lang, show_log=False)
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.warning(f"PaddleOCR not initialized ({str(e)}). Running in fallback/mock mode.")
            self.ocr_instance = None

    def extract_text(self, image: Any) -> OCRResult:
        if self.ocr_instance is None:
            # Fallback when running in environments without Paddle weights preloaded
            return OCRResult(
                raw_text="",
                regions=[],
                average_confidence=0.0,
                preprocessing_applied=[]
            )

        try:
            # PaddleOCR expects BGR or RGB image
            ocr_output = self.ocr_instance.ocr(image, cls=self.use_angle_cls)
            
            regions: List[OCRRegion] = []
            extracted_lines: List[str] = []
            confidences: List[float] = []

            if ocr_output and len(ocr_output) > 0 and ocr_output[0] is not None:
                for line_data in ocr_output[0]:
                    # line_data format: [bbox_coordinates, (text, confidence)]
                    # bbox format: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    bbox = line_data[0]
                    text, conf = line_data[1]

                    regions.append(OCRRegion(
                        text=str(text).strip(),
                        confidence=float(conf),
                        bounding_box=bbox
                    ))
                    extracted_lines.append(str(text).strip())
                    confidences.append(float(conf))

            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            full_text = "\n".join(extracted_lines)

            return OCRResult(
                raw_text=full_text,
                regions=regions,
                average_confidence=round(avg_conf, 3),
                preprocessing_applied=[]
            )
        except Exception as e:
            logger.error(f"Error executing PaddleOCR: {str(e)}")
            raise RuntimeError(f"PaddleOCR extraction failed: {str(e)}")


class MockOCREngine(BaseOCREngine):
    """
    Configurable mock OCR engine for deterministic unit testing without requiring GPU/PaddleOCR weights.
    """

    def __init__(self, predefined_result: Optional[OCRResult] = None):
        self.predefined_result = predefined_result

    def set_result(self, result: OCRResult):
        self.predefined_result = result

    def extract_text(self, image: Any) -> OCRResult:
        if self.predefined_result:
            return self.predefined_result
        return OCRResult(
            raw_text="Sample Product\nMRP: Rs. 50.00 (incl. of all taxes)\nNet Qty: 100 g\nPkd: 06/2026\nMfg by: ABC Foods Ltd, Madurai, Tamil Nadu 625001\nConsumer Care: care@abcfoods.com 1800-123-4567\nCountry of Origin: India",
            regions=[
                OCRRegion(text="Sample Product", confidence=0.98, bounding_box=[[10, 10], [200, 10], [200, 40], [10, 40]]),
                OCRRegion(text="MRP: Rs. 50.00 (incl. of all taxes)", confidence=0.96, bounding_box=[[10, 50], [300, 50], [300, 80], [10, 80]]),
                OCRRegion(text="Net Qty: 100 g", confidence=0.97, bounding_box=[[10, 90], [150, 90], [150, 120], [10, 120]]),
                OCRRegion(text="Pkd: 06/2026", confidence=0.95, bounding_box=[[10, 130], [140, 130], [140, 160], [10, 160]]),
                OCRRegion(text="Mfg by: ABC Foods Ltd, Madurai, Tamil Nadu 625001", confidence=0.94, bounding_box=[[10, 170], [450, 170], [450, 200], [10, 200]]),
                OCRRegion(text="Consumer Care: care@abcfoods.com 1800-123-4567", confidence=0.96, bounding_box=[[10, 210], [400, 210], [400, 240], [10, 240]]),
                OCRRegion(text="Country of Origin: India", confidence=0.99, bounding_box=[[10, 250], [250, 250], [250, 280], [10, 280]])
            ],
            average_confidence=0.96,
            preprocessing_applied=["standard", "clahe_contrast"]
        )
