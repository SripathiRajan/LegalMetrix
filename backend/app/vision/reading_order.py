from __future__ import annotations

import math
import logging
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple, Union
from collections import defaultdict

from app.vision.bbox_utils import BBoxUtils
from app.vision.spatial_analysis import SpatialAnalysis

if TYPE_CHECKING:
    from app.models.extracted_product import OCRRegion

logger = logging.getLogger(__name__)


class ReadingOrderResolver:
    """
    Orientation-Aware Reading Order Resolver:
      - Analyzes 4-point OCR polygon geometry to determine individual rotation angles
      - Clusters regions into logical blocks using SpatialAnalysis quadrant & spatial logic
      - Re-orders regions inside each cluster with rotation-aware axis sorting
        (top-to-bottom primary, left-to-right secondary for upright text;
         swaps axes when dominant angle is near 90°/270°)
      - Annotates each region with detected_angle_degrees, cluster_id, and reading_order_confidence
    """

    def __init__(self, line_tolerance_factor: float = 0.5):
        self.line_tolerance_factor = line_tolerance_factor

    @staticmethod
    def compute_polygon_angle(bbox: Union[List[List[float]], List[float]]) -> float:
        """
        Computes the rotation/orientation angle (0.0 to 359.9 degrees) from a 4-point polygon.
        The top edge vector (p0 -> p1) defines the reading baseline direction.
        Returns 0.0 for standard 2-point axis-aligned bounding boxes [xmin, ymin, xmax, ymax].
        """
        if not bbox:
            return 0.0

        if isinstance(bbox[0], (list, tuple)) and len(bbox) >= 2:
            p0 = bbox[0]
            p1 = bbox[1]
            dx = float(p1[0] - p0[0])
            dy = float(p1[1] - p0[1])

            # Distance between p0 and p1 (vector magnitude)
            if abs(dx) < 1e-5 and abs(dy) < 1e-5:
                return 0.0

            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad) % 360.0
            return round(angle_deg, 1)

        return 0.0

    @staticmethod
    def is_vertical_orientation(angle: float) -> bool:
        """
        Returns True if the angle represents a vertical/rotated orientation (~90° or ~270°).
        Angle range: [45.0°, 135.0°) or [225.0°, 315.0°).
        """
        norm_angle = angle % 360.0
        return (45.0 <= norm_angle < 135.0) or (225.0 <= norm_angle < 315.0)

    def _cluster_regions(
        self,
        regions: List[OCRRegion],
        img_width: int,
        img_height: int
    ) -> Dict[str, List[Tuple[OCRRegion, float]]]:
        """
        Clusters regions into logical blocks using SpatialAnalysis quadrant/positioning
        and orientation angle buckets.
        """
        clusters: Dict[str, List[Tuple[OCRRegion, float]]] = defaultdict(list)

        for region in regions:
            angle = self.compute_polygon_angle(region.bounding_box)
            is_vert = self.is_vertical_orientation(angle)

            # Classify spatial positioning and quadrant
            spatial_info = SpatialAnalysis.classify_position(
                region.bounding_box,
                img_width=img_width,
                img_height=img_height
            )
            quadrant = spatial_info.get("quadrant", "TOP_LEFT")
            orientation_tag = "vert" if is_vert else "horiz"
            cluster_id = f"block_{quadrant.lower()}_{orientation_tag}"

            clusters[cluster_id].append((region, angle))

        return clusters

    def _sort_horizontal_cluster(
        self,
        items: List[Tuple[OCRRegion, float]]
    ) -> List[Tuple[OCRRegion, float]]:
        """
        Orders horizontal/upright text:
        Primary: Top-to-Bottom (y)
        Secondary: Left-to-Right (x)
        Groups lines with close y-coordinates.
        """
        if not items:
            return []

        # Calculate representative line height
        heights = []
        for r, _ in items:
            _, h = BBoxUtils.get_dimensions(r.bounding_box)
            if h > 0:
                heights.append(h)
        median_h = sorted(heights)[len(heights) // 2] if heights else 20.0
        line_threshold = max(8.0, median_h * self.line_tolerance_factor)

        # Sort all items initially by center y, then center x
        def _get_coords(item: Tuple[OCRRegion, float]):
            cx, cy = BBoxUtils.get_center(item[0].bounding_box)
            return cy, cx

        sorted_by_y = sorted(items, key=_get_coords)

        # Group into lines
        lines: List[List[Tuple[OCRRegion, float]]] = []
        for item in sorted_by_y:
            _, cy = BBoxUtils.get_center(item[0].bounding_box)
            if not lines:
                lines.append([item])
            else:
                last_line = lines[-1]
                avg_line_y = sum(
                    BBoxUtils.get_center(x[0].bounding_box)[1] for x in last_line
                ) / len(last_line)
                if abs(cy - avg_line_y) <= line_threshold:
                    last_line.append(item)
                else:
                    lines.append([item])

        # Sort each line left-to-right (x)
        ordered_items: List[Tuple[OCRRegion, float]] = []
        for line in lines:
            line_sorted = sorted(
                line,
                key=lambda x: BBoxUtils.get_center(x[0].bounding_box)[0]
            )
            ordered_items.extend(line_sorted)

        return ordered_items

    def _sort_vertical_cluster(
        self,
        items: List[Tuple[OCRRegion, float]]
    ) -> List[Tuple[OCRRegion, float]]:
        """
        Orders vertical/rotated (90°/270°) text with swapped axes:
        Primary: Left-to-Right / Column (x)
        Secondary: Top-to-Bottom (y)
        Groups columns with close x-coordinates.
        """
        if not items:
            return []

        # Calculate representative column width
        widths = []
        for r, _ in items:
            w, _ = BBoxUtils.get_dimensions(r.bounding_box)
            if w > 0:
                widths.append(w)
        median_w = sorted(widths)[len(widths) // 2] if widths else 20.0
        col_threshold = max(8.0, median_w * self.line_tolerance_factor)

        # Sort all items initially by center x, then center y
        def _get_coords(item: Tuple[OCRRegion, float]):
            cx, cy = BBoxUtils.get_center(item[0].bounding_box)
            return cx, cy

        sorted_by_x = sorted(items, key=_get_coords)

        # Group into columns
        columns: List[List[Tuple[OCRRegion, float]]] = []
        for item in sorted_by_x:
            cx, _ = BBoxUtils.get_center(item[0].bounding_box)
            if not columns:
                columns.append([item])
            else:
                last_col = columns[-1]
                avg_col_x = sum(
                    BBoxUtils.get_center(x[0].bounding_box)[0] for x in last_col
                ) / len(last_col)
                if abs(cx - avg_col_x) <= col_threshold:
                    last_col.append(item)
                else:
                    columns.append([item])

        # Sort each column top-to-bottom (y)
        ordered_items: List[Tuple[OCRRegion, float]] = []
        for col in columns:
            col_sorted = sorted(
                col,
                key=lambda x: BBoxUtils.get_center(x[0].bounding_box)[1]
            )
            ordered_items.extend(col_sorted)

        return ordered_items

    def resolve(
        self,
        regions: List[OCRRegion],
        img_width: Optional[int] = None,
        img_height: Optional[int] = None
    ) -> List[OCRRegion]:
        """
        Resolves the orientation-aware reading order across all given OCRRegions.
        Returns the re-ordered list of regions annotated with detected_angle_degrees,
        cluster_id, and reading_order_confidence.
        """
        if not regions:
            return []

        from app.models.extracted_product import OCRRegion

        # If image dimensions are not provided, estimate them from bounding boxes
        if not img_width or not img_height or img_width <= 0 or img_height <= 0:
            all_bboxes = [r.bounding_box for r in regions if r.bounding_box]
            if all_bboxes:
                merged = BBoxUtils.merge_bboxes(all_bboxes)
                img_width = max(100, int(merged[2]) + 50)
                img_height = max(100, int(merged[3]) + 50)
            else:
                img_width, img_height = 1000, 1000

        # 1. Cluster regions by quadrant and orientation
        clusters = self._cluster_regions(regions, img_width, img_height)

        # 2. Canonical cluster ordering:
        # Standard Reading Order: TOP_LEFT -> TOP_RIGHT -> BOTTOM_LEFT -> BOTTOM_RIGHT
        # Within each quadrant, prioritize horizontal/upright blocks before vertical sidebars
        quadrant_order = [
            "block_top_left_horiz",
            "block_top_left_vert",
            "block_top_right_horiz",
            "block_top_right_vert",
            "block_bottom_left_horiz",
            "block_bottom_left_vert",
            "block_bottom_right_horiz",
            "block_bottom_right_vert"
        ]

        # Order clusters according to canonical order, then any custom remaining keys
        sorted_cluster_keys = [k for k in quadrant_order if k in clusters]
        remaining_keys = sorted([k for k in clusters if k not in sorted_cluster_keys])
        all_ordered_keys = sorted_cluster_keys + remaining_keys

        # 3. Sort regions inside each cluster with rotation-aware reading order
        reordered_regions: List[OCRRegion] = []

        for cluster_id in all_ordered_keys:
            items = clusters[cluster_id]
            is_vert = cluster_id.endswith("_vert")

            if is_vert:
                ordered_items = self._sort_vertical_cluster(items)
            else:
                ordered_items = self._sort_horizontal_cluster(items)

            for region, angle in ordered_items:
                annotated_region = OCRRegion(
                    text=region.text,
                    confidence=region.confidence,
                    bounding_box=region.bounding_box,
                    detected_angle_degrees=angle,
                    cluster_id=cluster_id,
                    reading_order_confidence=0.95
                )
                reordered_regions.append(annotated_region)

        return reordered_regions
