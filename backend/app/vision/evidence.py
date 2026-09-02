import base64
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field

from app.vision.bbox_utils import BBoxUtils
from app.vision.readability import ReadabilityAnalyzer, ReadabilityStatus
from app.vision.spatial_analysis import SpatialAnalysis

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class VisualEvidence(BaseModel):
    """
    Visual evidence linking an extracted declaration to image coordinates,
    spatial location, readability, and original image resolution.
    """
    image_width: int = Field(..., description="Width of original input image in pixels")
    image_height: int = Field(..., description="Height of original input image in pixels")
    bounding_box: List[float] = Field(default_factory=list, description="Axis-aligned bounding box [xmin, ymin, xmax, ymax]")
    normalized_bbox: List[float] = Field(default_factory=list, description="Normalized coordinates [0.0 - 1.0]")
    text_height_pixels: float = Field(default=0.0, description="Estimated declaration text height in pixels")
    ocr_confidence: float = Field(default=0.0, description="OCR confidence for this declaration")
    readability_status: ReadabilityStatus = Field(default=ReadabilityStatus.READABLE, description="Heuristic readability assessment")
    position: Dict[str, Any] = Field(default_factory=dict, description="Spatial position (horizontal, vertical, quadrant, center)")
    source_text: Optional[str] = Field(None, description="Exact OCR text detected in image region")
    has_evidence: bool = Field(default=True, description="False if declaration was not detected in image OCR")


class EvidenceAnnotator:
    """
    Generates annotated verification images highlighting detected declarations
    with color-coded bounding boxes according to compliance / verification status.
    """

    # Centralized color palette (BGR format for OpenCV)
    STATUS_COLORS = {
        "PASS": (46, 204, 113),                  # Bright Green
        "WARNING": (241, 196, 15),               # Amber Yellow
        "FAIL": (231, 76, 60),                   # Red
        "REQUIRES_HUMAN_VERIFICATION": (52, 152, 219), # Bright Blue
        "NOT_APPLICABLE": (149, 165, 166)        # Gray
    }

    @staticmethod
    def annotate_image(
        image_array: Any,
        annotated_fields: List[Dict[str, Any]],
        output_format: str = "png"
    ) -> Tuple[Any, str]:
        """
        Draws labeled bounding boxes on image.
        Returns:
          - Annotated image numpy array
          - Base64 data URI string for direct API display
        """
        if not CV2_AVAILABLE or image_array is None:
            return None, ""

        canvas = image_array.copy()
        h, w = canvas.shape[:2]

        for item in annotated_fields:
            bbox = item.get("bounding_box", [])
            label = item.get("label", "DECLARATION")
            status = item.get("status", "PASS")

            if not bbox or len(bbox) != 4:
                continue

            xmin, ymin, xmax, ymax = map(int, [max(0, bbox[0]), max(0, bbox[1]), min(w, bbox[2]), min(h, bbox[3])])
            if xmax <= xmin or ymax <= ymin:
                continue

            color = EvidenceAnnotator.STATUS_COLORS.get(status, (52, 152, 219))

            # Draw rectangle with thickness scaled to image resolution
            thickness = max(2, int(min(w, h) / 400))
            cv2.rectangle(canvas, (xmin, ymin), (xmax, ymax), color, thickness)

            # Draw label banner
            font_scale = max(0.4, min(w, h) / 1200.0)
            text_str = f"{label}: {status}"
            (tw, th), baseline = cv2.getTextSize(text_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)

            banner_y1 = max(0, ymin - th - baseline - 4)
            banner_y2 = ymin
            banner_x2 = min(w, xmin + tw + 6)

            cv2.rectangle(canvas, (xmin, banner_y1), (banner_x2, banner_y2), color, -1)
            cv2.putText(
                canvas,
                text_str,
                (xmin + 3, banner_y2 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # Encode to base64
        ext = f".{output_format}"
        success, buffer = cv2.imencode(ext, canvas)
        if success:
            b64_str = f"data:image/{output_format};base64,{base64.b64encode(buffer).decode('utf-8')}"
        else:
            b64_str = ""

        return canvas, b64_str


class EvidenceManager:
    """
    Constructs VisualEvidence objects linking extracted fields,
    OCR results, and rule evaluations.
    """

    def __init__(self, readability_analyzer: Optional[ReadabilityAnalyzer] = None):
        self.readability_analyzer = readability_analyzer or ReadabilityAnalyzer()

    def build_evidence(
        self,
        bounding_boxes: List[Union[List[List[float]], List[float]]],
        confidence: float,
        source_text: Optional[str],
        img_width: int,
        img_height: int,
        image_array: Optional[Any] = None,
        scale_factor: float = 1.0
    ) -> VisualEvidence:
        """
        Builds a comprehensive VisualEvidence object.
        Correctly transforms coordinates back to original image space if scaled.
        """
        if not bounding_boxes:
            return VisualEvidence(
                image_width=img_width,
                image_height=img_height,
                bounding_box=[],
                normalized_bbox=[],
                text_height_pixels=0.0,
                ocr_confidence=0.0,
                readability_status=ReadabilityStatus.UNREADABLE,
                position={"horizontal": "UNKNOWN", "vertical": "UNKNOWN", "quadrant": "UNKNOWN", "normalized_center": [0.5, 0.5]},
                source_text=None,
                has_evidence=False
            )

        # Merge boxes and scale back to original image coordinates
        merged_bbox = BBoxUtils.merge_bboxes(bounding_boxes)
        original_bbox = BBoxUtils.scale_bbox_to_original(merged_bbox, scale_factor)

        norm_bbox = BBoxUtils.normalize_bbox(original_bbox, img_width, img_height)
        position = SpatialAnalysis.classify_position(original_bbox, img_width, img_height)
        readability = self.readability_analyzer.analyze_readability(
            confidence=confidence,
            bbox=original_bbox,
            img_width=img_width,
            img_height=img_height,
            image_array=image_array
        )

        return VisualEvidence(
            image_width=img_width,
            image_height=img_height,
            bounding_box=original_bbox,
            normalized_bbox=norm_bbox,
            text_height_pixels=readability["text_height_pixels"],
            ocr_confidence=readability["ocr_confidence"],
            readability_status=readability["status"],
            position=position,
            source_text=source_text,
            has_evidence=True
        )
