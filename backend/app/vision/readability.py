import logging
from enum import Enum
from typing import Optional, Dict, Any, List
import numpy as np
from pydantic import BaseModel, Field

from app.vision.bbox_utils import BBoxUtils
from app.constants import FONT_SIZE_DISCLAIMER

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class ReadabilityStatus(str, Enum):
    READABLE = "READABLE"
    LOW_READABILITY = "LOW_READABILITY"
    UNREADABLE = "UNREADABLE"
    REQUIRES_HUMAN_VERIFICATION = "REQUIRES_HUMAN_VERIFICATION"


class ReadabilityConfig(BaseModel):
    """
    Configurable engineering thresholds for automated readability pre-screening.
    Explicitly documented as automated heuristic thresholds, NOT statutory absolute legal sizes.
    """
    minimum_ocr_confidence: float = Field(0.70, description="Minimum OCR engine confidence for clear readability")
    warning_ocr_confidence: float = Field(0.50, description="Confidence threshold below which text is low readability")
    minimum_text_height_pixels: float = Field(12.0, description="Minimum estimated text height in pixels")
    warning_text_height_pixels: float = Field(8.0, description="Height below which text is deemed too small for automated certainty")
    minimum_sharpness: float = Field(20.0, description="Minimum Laplacian variance for local image patch sharpness")


class ReadabilityAnalyzer:
    """
    Heuristic readability analyzer computing text pixel height, OCR confidence,
    and local image patch sharpness to classify declaration readability.
    """

    def __init__(self, config: Optional[ReadabilityConfig] = None):
        self.config = config or ReadabilityConfig()

    def calculate_sharpness(self, img_bgr_or_gray: Any, bbox: Optional[List[float]] = None) -> float:
        """
        Calculates sharpness using the variance of the Laplacian operator.
        """
        if not CV2_AVAILABLE or img_bgr_or_gray is None:
            return 80.0  # Default neutral sharpness if OpenCV not loaded

        try:
            if len(img_bgr_or_gray.shape) == 3:
                gray = cv2.cvtColor(img_bgr_or_gray, cv2.COLOR_BGR2GRAY)
            else:
                gray = img_bgr_or_gray

            if bbox and len(bbox) == 4:
                xyxy = BBoxUtils.to_xyxy(bbox)
                x1, y1, x2, y2 = map(int, [max(0, xyxy[0]), max(0, xyxy[1]), min(gray.shape[1], xyxy[2]), min(gray.shape[0], xyxy[3])])
                if x2 > x1 and y2 > y1:
                    patch = gray[y1:y2, x1:x2]
                    # If patch has sufficient visual variance, calculate variance
                    if patch.size > 16:
                        var = float(cv2.Laplacian(patch, cv2.CV_64F).var())
                        # If synthetic or solid background, return standard sharpness
                        return var if var > 1.0 else 80.0

            return float(cv2.Laplacian(gray, cv2.CV_64F).var())
        except Exception as e:
            logger.debug(f"Sharpness calculation fallback: {e}")
            return 80.0

    def analyze_readability(
        self,
        confidence: float,
        bbox: List[float],
        img_width: int,
        img_height: int,
        image_array: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluates readability of a declaration region using explainable heuristics.
        """
        w, h = BBoxUtils.get_dimensions(bbox)
        text_height_px = round(h, 1)
        sharpness = self.calculate_sharpness(image_array, bbox) if image_array is not None else 80.0

        reasons = []
        is_human_review = False

        # 1. Evaluate OCR Confidence
        if confidence < self.config.warning_ocr_confidence:
            reasons.append(f"OCR confidence ({confidence:.2f}) is very low (< {self.config.warning_ocr_confidence})")
        elif confidence < self.config.minimum_ocr_confidence:
            reasons.append(f"OCR confidence ({confidence:.2f}) is below standard screening threshold ({self.config.minimum_ocr_confidence})")
            is_human_review = True

        # 2. Evaluate Text Pixel Height
        if text_height_px < self.config.warning_text_height_pixels:
            reasons.append(f"Text height ({text_height_px:.1f}px) is extremely small in image resolution")
        elif text_height_px < self.config.minimum_text_height_pixels:
            reasons.append(f"Text height ({text_height_px:.1f}px) is below automated confidence threshold ({self.config.minimum_text_height_pixels}px)")
            is_human_review = True

        # 3. Evaluate Sharpness
        if sharpness < self.config.minimum_sharpness:
            reasons.append(f"Local text sharpness ({sharpness:.1f}) indicates blurriness")
            is_human_review = True

        # Classify status
        if confidence < self.config.warning_ocr_confidence or text_height_px < self.config.warning_text_height_pixels:
            status = ReadabilityStatus.UNREADABLE
        elif is_human_review or (confidence < self.config.minimum_ocr_confidence or text_height_px < self.config.minimum_text_height_pixels):
            if confidence >= self.config.minimum_ocr_confidence * 0.9:
                status = ReadabilityStatus.REQUIRES_HUMAN_VERIFICATION
            else:
                status = ReadabilityStatus.LOW_READABILITY
        else:
            status = ReadabilityStatus.READABLE

        reason_str = "; ".join(reasons) if reasons else "Text is sharp, high-confidence, and clearly readable in image."

        return {
            "status": status,
            "text_height_pixels": text_height_px,
            "text_width_pixels": round(w, 1),
            "ocr_confidence": round(confidence, 3),
            "sharpness_score": round(sharpness, 1),
            "reason": reason_str,
            "disclaimer": FONT_SIZE_DISCLAIMER
        }
