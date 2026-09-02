from typing import List, Dict, Any, Tuple
from app.vision.bbox_utils import BBoxUtils


class SpatialAnalysis:
    """
    Spatial positioning and quadrant analysis for Legal Metrology package declarations.
    Determines relative position (horizontal, vertical, quadrant, normalized center)
    to verify declaration placement without asserting unmandated legal claims.
    """

    @staticmethod
    def classify_position(
        bbox: List[float],
        img_width: int,
        img_height: int
    ) -> Dict[str, Any]:
        """
        Calculates normalized center, horizontal, vertical and quadrant placement.
        """
        if img_width <= 0 or img_height <= 0 or not bbox:
            return {
                "horizontal": "UNKNOWN",
                "vertical": "UNKNOWN",
                "quadrant": "UNKNOWN",
                "normalized_center": [0.5, 0.5]
            }

        cx, cy = BBoxUtils.get_center(bbox)
        norm_cx = round(cx / img_width, 3)
        norm_cy = round(cy / img_height, 3)

        # Horizontal alignment
        if norm_cx < 0.35:
            h_pos = "LEFT"
        elif norm_cx > 0.65:
            h_pos = "RIGHT"
        else:
            h_pos = "CENTER"

        # Vertical alignment
        if norm_cy < 0.35:
            v_pos = "TOP"
        elif norm_cy > 0.65:
            v_pos = "BOTTOM"
        else:
            v_pos = "MIDDLE"

        # Quadrant classification
        if norm_cx <= 0.5 and norm_cy <= 0.5:
            quadrant = "TOP_LEFT"
        elif norm_cx > 0.5 and norm_cy <= 0.5:
            quadrant = "TOP_RIGHT"
        elif norm_cx <= 0.5 and norm_cy > 0.5:
            quadrant = "BOTTOM_LEFT"
        else:
            quadrant = "BOTTOM_RIGHT"

        return {
            "horizontal": h_pos,
            "vertical": v_pos,
            "quadrant": quadrant,
            "normalized_center": [norm_cx, norm_cy]
        }
