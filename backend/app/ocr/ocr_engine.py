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
    PaddleOCR / RapidOCR implementation for high-accuracy text and bounding box detection.
    """

    def __init__(self, lang: str = "en", use_angle_cls: bool = True):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.ocr_instance = None
        self.rapid_ocr = None
        self._initialize_engine()

    def _initialize_engine(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            logger.info("Initializing RapidOCR ONNX deep-learning engine...")
            self.rapid_ocr = RapidOCR()
            logger.info("RapidOCR engine initialized successfully.")
            return
        except Exception as e:
            logger.debug(f"RapidOCR initialization failed: {e}")

        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR engine...")
            self.ocr_instance = PaddleOCR(use_angle_cls=self.use_angle_cls, lang=self.lang, show_log=False)
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.warning(f"PaddleOCR not initialized ({str(e)}). Running in fallback mode.")
            self.ocr_instance = None

    def extract_text(self, image: Any) -> OCRResult:
        if self.rapid_ocr is not None:
            try:
                ocr_output, _ = self.rapid_ocr(image)
                regions: List[OCRRegion] = []
                extracted_lines: List[str] = []
                confidences: List[float] = []

                if ocr_output:
                    for line_data in ocr_output:
                        bbox, text, conf = line_data
                        text_str = str(text).strip()
                        if text_str:
                            bbox_list = [[float(p[0]), float(p[1])] for p in bbox]
                            conf_val = float(conf)
                            regions.append(OCRRegion(
                                text=text_str,
                                confidence=round(conf_val, 4),
                                bounding_box=bbox_list
                            ))
                            extracted_lines.append(text_str)
                            confidences.append(conf_val)

                avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
                full_text = "\n".join(extracted_lines)

                return OCRResult(
                    raw_text=full_text,
                    regions=regions,
                    average_confidence=round(avg_conf, 3),
                    preprocessing_applied=["rapidocr_onnx"]
                )
            except Exception as e:
                logger.error(f"Error executing RapidOCR: {str(e)}")

        if self.ocr_instance is not None:
            try:
                ocr_output = self.ocr_instance.ocr(image, cls=self.use_angle_cls)
                regions: List[OCRRegion] = []
                extracted_lines: List[str] = []
                confidences: List[float] = []

                if ocr_output and len(ocr_output) > 0 and ocr_output[0] is not None:
                    for line_data in ocr_output[0]:
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
                    preprocessing_applied=["paddleocr"]
                )
            except Exception as e:
                logger.error(f"Error executing PaddleOCR: {str(e)}")



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


class EasyOCREngine(BaseOCREngine):
    """
    EasyOCR implementation with lazy loading and fallback handling.
    Supports multilingual text detection and extraction using deep learning CRNN models.
    """

    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = False):
        self.languages = languages or ["en"]
        self.gpu = gpu
        self.ocr_instance = None
        self._initialize_engine()

    def _initialize_engine(self):
        try:
            import easyocr
            logger.info("Initializing EasyOCR engine...")
            self.ocr_instance = easyocr.Reader(self.languages, gpu=self.gpu)
            logger.info("EasyOCR engine initialized successfully.")
        except Exception as e:
            logger.warning(f"EasyOCR not initialized ({str(e)}). Running in fallback/mock mode.")
            self.ocr_instance = None

    def extract_text(self, image: Any) -> OCRResult:
        if self.ocr_instance is None:
            # Fallback when running in environments without EasyOCR dependencies
            return OCRResult(
                raw_text="",
                regions=[],
                average_confidence=0.0,
                preprocessing_applied=[]
            )

        try:
            ocr_output = self.ocr_instance.readtext(image)

            regions: List[OCRRegion] = []
            extracted_lines: List[str] = []
            confidences: List[float] = []

            if ocr_output:
                for line_data in ocr_output:
                    # line_data format: (bbox, text, confidence)
                    # bbox: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    bbox, text, conf = line_data
                    text_str = str(text).strip()
                    if not text_str:
                        continue

                    if isinstance(bbox[0], (list, tuple)):
                        bbox_list = [[float(p[0]), float(p[1])] for p in bbox]
                    else:
                        bbox_list = [float(x) for x in bbox]

                    conf_val = float(conf)

                    regions.append(OCRRegion(
                        text=text_str,
                        confidence=round(conf_val, 4),
                        bounding_box=bbox_list
                    ))
                    extracted_lines.append(text_str)
                    confidences.append(conf_val)

            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            full_text = "\n".join(extracted_lines)

            return OCRResult(
                raw_text=full_text,
                regions=regions,
                average_confidence=round(avg_conf, 3),
                preprocessing_applied=[]
            )
        except Exception as e:
            logger.error(f"Error executing EasyOCR: {str(e)}")
            raise RuntimeError(f"EasyOCR extraction failed: {str(e)}")


class TesseractOCREngine(BaseOCREngine):
    """
    Tesseract OCR implementation (via pytesseract) with lazy loading and fallback handling.
    """

    def __init__(self, lang: str = "eng", config: str = "--oem 3 --psm 6"):
        self.lang = lang
        self.config = config
        self.ocr_instance = None
        self._initialize_engine()

    def _initialize_engine(self):
        try:
            import pytesseract
            logger.info("Initializing Tesseract OCR engine...")
            self.ocr_instance = pytesseract
            logger.info("Tesseract OCR engine initialized successfully.")
        except Exception as e:
            logger.warning(f"Tesseract OCR not initialized ({str(e)}). Running in fallback/mock mode.")
            self.ocr_instance = None

    def extract_text(self, image: Any) -> OCRResult:
        if self.ocr_instance is None:
            # Fallback when running in environments without pytesseract/Tesseract installed
            return OCRResult(
                raw_text="",
                regions=[],
                average_confidence=0.0,
                preprocessing_applied=[]
            )

        try:
            data = self.ocr_instance.image_to_data(
                image,
                lang=self.lang,
                config=self.config,
                output_type=self.ocr_instance.Output.DICT
            )

            regions: List[OCRRegion] = []
            extracted_lines: List[str] = []
            confidences: List[float] = []

            n_boxes = len(data.get("text", []))
            for i in range(n_boxes):
                text = str(data["text"][i]).strip()
                conf_val = data["conf"][i]
                try:
                    conf_float = float(conf_val)
                except (ValueError, TypeError):
                    conf_float = -1.0

                # Tesseract returns conf = -1 for structure blocks / empty strings
                if not text or conf_float < 0:
                    continue

                # Normalize confidence from 0-100 to 0.0-1.0
                norm_conf = min(1.0, max(0.0, conf_float / 100.0))

                x = float(data["left"][i])
                y = float(data["top"][i])
                w = float(data["width"][i])
                h = float(data["height"][i])
                bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

                regions.append(OCRRegion(
                    text=text,
                    confidence=round(norm_conf, 4),
                    bounding_box=bbox
                ))
                extracted_lines.append(text)
                confidences.append(norm_conf)

            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            full_text = "\n".join(extracted_lines)

            return OCRResult(
                raw_text=full_text,
                regions=regions,
                average_confidence=round(avg_conf, 3),
                preprocessing_applied=[]
            )
        except Exception as e:
            logger.warning(f"Tesseract OCR execution failed ({str(e)}). Returning empty fallback.")
            return OCRResult(
                raw_text="",
                regions=[],
                average_confidence=0.0,
                preprocessing_applied=[]
            )

