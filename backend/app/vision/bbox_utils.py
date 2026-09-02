from typing import List, Tuple, Optional, Union
import numpy as np


class BBoxUtils:
    """
    Utilities for validating, calculating geometry, normalizing,
    transforming, and merging OCR bounding boxes.
    """

    @staticmethod
    def to_xyxy(bbox: Union[List[List[float]], List[float]]) -> List[float]:
        """
        Converts any bounding box format (4-point polygon [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        or [x1, y1, x2, y2]) into standard axis-aligned [xmin, ymin, xmax, ymax].
        """
        if not bbox:
            return [0.0, 0.0, 0.0, 0.0]

        # Case 1: 4-point polygon format from PaddleOCR: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        if isinstance(bbox[0], (list, tuple)):
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            return [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]

        # Case 2: [x1, y1, x2, y2]
        if len(bbox) == 4:
            return [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]

        return [0.0, 0.0, 0.0, 0.0]

    @staticmethod
    def validate_bbox(bbox: List[float], img_width: int, img_height: int) -> bool:
        """
        Validates if [xmin, ymin, xmax, ymax] is valid within image boundaries.
        """
        if not bbox or len(bbox) != 4:
            return False
        xmin, ymin, xmax, ymax = bbox
        if xmax <= xmin or ymax <= ymin:
            return False
        if xmin < 0 or ymin < 0:
            return False
        if img_width > 0 and xmax > img_width + 5:  # small pixel tolerance
            return False
        if img_height > 0 and ymax > img_height + 5:
            return False
        return True

    @staticmethod
    def get_dimensions(bbox: List[float]) -> Tuple[float, float]:
        """
        Returns (width, height) in pixels.
        """
        xyxy = BBoxUtils.to_xyxy(bbox)
        width = max(0.0, xyxy[2] - xyxy[0])
        height = max(0.0, xyxy[3] - xyxy[1])
        return width, height

    @staticmethod
    def get_area(bbox: List[float]) -> float:
        """
        Returns area in square pixels.
        """
        w, h = BBoxUtils.get_dimensions(bbox)
        return w * h

    @staticmethod
    def get_center(bbox: List[float]) -> Tuple[float, float]:
        """
        Returns center point (cx, cy).
        """
        xyxy = BBoxUtils.to_xyxy(bbox)
        return (xyxy[0] + xyxy[2]) / 2.0, (xyxy[1] + xyxy[3]) / 2.0

    @staticmethod
    def normalize_bbox(bbox: List[float], img_width: int, img_height: int) -> List[float]:
        """
        Normalizes [xmin, ymin, xmax, ymax] coordinates to [0.0, 1.0] relative to image dimensions.
        """
        if img_width <= 0 or img_height <= 0:
            return [0.0, 0.0, 0.0, 0.0]

        xyxy = BBoxUtils.to_xyxy(bbox)
        return [
            round(max(0.0, min(1.0, xyxy[0] / img_width)), 4),
            round(max(0.0, min(1.0, xyxy[1] / img_height)), 4),
            round(max(0.0, min(1.0, xyxy[2] / img_width)), 4),
            round(max(0.0, min(1.0, xyxy[3] / img_height)), 4)
        ]

    @staticmethod
    def scale_bbox_to_original(
        bbox: Union[List[List[float]], List[float]],
        scale_factor: float
    ) -> List[float]:
        """
        Transforms coordinates from scaled preprocessed image back to original image coordinates.
        scale_factor = preprocessed_dim / original_dim
        """
        if scale_factor <= 0 or scale_factor == 1.0:
            return BBoxUtils.to_xyxy(bbox)

        xyxy = BBoxUtils.to_xyxy(bbox)
        inv_scale = 1.0 / scale_factor
        return [
            round(xyxy[0] * inv_scale, 1),
            round(xyxy[1] * inv_scale, 1),
            round(xyxy[2] * inv_scale, 1),
            round(xyxy[3] * inv_scale, 1)
        ]

    @staticmethod
    def merge_bboxes(bboxes: List[Union[List[List[float]], List[float]]]) -> List[float]:
        """
        Merges multiple bounding boxes into an encompassing bounding box [xmin, ymin, xmax, ymax].
        """
        if not bboxes:
            return [0.0, 0.0, 0.0, 0.0]

        xyxy_list = [BBoxUtils.to_xyxy(b) for b in bboxes if b]
        if not xyxy_list:
            return [0.0, 0.0, 0.0, 0.0]

        min_x = min(b[0] for b in xyxy_list)
        min_y = min(b[1] for b in xyxy_list)
        max_x = max(b[2] for b in xyxy_list)
        max_y = max(b[3] for b in xyxy_list)

        return [round(min_x, 1), round(min_y, 1), round(max_x, 1), round(max_y, 1)]
