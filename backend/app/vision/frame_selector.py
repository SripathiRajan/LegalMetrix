import logging
import os
import tempfile
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
from pydantic import BaseModel, Field, ConfigDict

from app.models.extracted_product import OCRResult, OCRRegion
from app.vision.readability import ReadabilityAnalyzer
from app.vision.reading_order import ReadingOrderResolver
from app.vision.bbox_utils import BBoxUtils

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class SelectedFrame(BaseModel):
    """
    Metadata and image data for an optimally selected video keyframe.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    frame_index: int = Field(..., description="0-indexed frame index in the source video stream")
    timestamp_seconds: float = Field(..., description="Timestamp in seconds within the video")
    sharpness_score: float = Field(..., description="Laplacian variance sharpness metric")
    image_array: Optional[Any] = Field(None, description="OpenCV BGR numpy image array")


class FrameSelector:
    """
    Video Keyframe Selector and Multi-Frame OCR Merger:
      - Samples video frames and scores clarity/sharpness reusing ReadabilityAnalyzer logic
      - Employs temporal windowed peak selection to maximize diversity and legibility
      - Merges candidate OCR regions across frames with IoU > 0.5 consensus (highest confidence wins)
      - Resolves spatial reading order across fused multi-frame regions
    """

    def __init__(
        self,
        readability_analyzer: Optional[ReadabilityAnalyzer] = None,
        reading_order_resolver: Optional[ReadingOrderResolver] = None,
        iou_threshold: float = 0.5
    ):
        self.readability_analyzer = readability_analyzer or ReadabilityAnalyzer()
        self.reading_order_resolver = reading_order_resolver or ReadingOrderResolver()
        self.iou_threshold = iou_threshold

    def calculate_sharpness(self, frame: Any) -> float:
        """
        Reuses existing ReadabilityAnalyzer sharpness logic (Laplacian variance).
        """
        return self.readability_analyzer.calculate_sharpness(frame)

    def extract_keyframes(
        self,
        video_source: Union[str, bytes],
        max_frames: int = 3,
        sample_fps: float = 2.0
    ) -> List[SelectedFrame]:
        """
        Extracts top `max_frames` sharpest keyframes from a video file path or video bytes buffer.
        """
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV (cv2) is required for video frame processing.")

        temp_file_path = None
        try:
            if isinstance(video_source, bytes):
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
                    tf.write(video_source)
                    temp_file_path = tf.name
                video_path = temp_file_path
            else:
                video_path = video_source

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video source at {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
            step = max(1, int(round(fps / max(0.1, sample_fps))))

            sampled_candidates: List[Tuple[int, float, float, np.ndarray]] = []
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % step == 0:
                    timestamp = frame_idx / fps
                    sharpness = self.calculate_sharpness(frame)
                    sampled_candidates.append((frame_idx, timestamp, sharpness, frame))

                frame_idx += 1

            cap.release()

            if not sampled_candidates:
                return []

            # If total sampled frames <= requested max_frames, return all
            if len(sampled_candidates) <= max_frames:
                return [
                    SelectedFrame(
                        frame_index=idx,
                        timestamp_seconds=round(ts, 2),
                        sharpness_score=round(sh, 2),
                        image_array=img
                    )
                    for idx, ts, sh, img in sampled_candidates
                ]

            # Partition sampled frames into `max_frames` uniform temporal buckets
            # and pick the sharpest frame within each bucket
            bucket_size = len(sampled_candidates) / float(max_frames)
            selected: List[SelectedFrame] = []

            for b in range(max_frames):
                start_i = int(b * bucket_size)
                end_i = int((b + 1) * bucket_size) if b < max_frames - 1 else len(sampled_candidates)
                bucket = sampled_candidates[start_i:end_i]
                if bucket:
                    best_in_bucket = max(bucket, key=lambda x: x[2])
                    selected.append(
                        SelectedFrame(
                            frame_index=best_in_bucket[0],
                            timestamp_seconds=round(best_in_bucket[1], 2),
                            sharpness_score=round(best_in_bucket[2], 2),
                            image_array=best_in_bucket[3]
                        )
                    )

            return selected
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass

    def merge_multi_frame_ocr(
        self,
        frame_ocr_results: List[OCRResult],
        iou_threshold: Optional[float] = None
    ) -> OCRResult:
        """
        Merges OCR results across multiple video frames:
          - Gathers regions from all candidate frames
          - Clusters regions with IoU > iou_threshold
          - Within each cluster, the highest-confidence text wins (same logic as OCREnsemble)
          - Applies ReadingOrderResolver to order fused declarations
        """
        thresh = iou_threshold if iou_threshold is not None else self.iou_threshold

        all_regions: List[OCRRegion] = []
        for ocr_res in frame_ocr_results:
            if ocr_res and ocr_res.regions:
                all_regions.extend(ocr_res.regions)

        if not all_regions:
            return OCRResult(
                raw_text="",
                regions=[],
                average_confidence=0.0,
                preprocessing_applied=["video_frame_fusion"]
            )

        # Cluster regions across frames by IoU
        clusters: List[List[OCRRegion]] = []
        for region in all_regions:
            best_match_idx = -1
            best_iou = thresh

            for c_idx, cluster in enumerate(clusters):
                for c_region in cluster:
                    iou = BBoxUtils.calculate_iou(region.bounding_box, c_region.bounding_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_match_idx = c_idx

            if best_match_idx >= 0:
                clusters[best_match_idx].append(region)
            else:
                clusters.append([region])

        # Highest confidence text wins per matched cluster
        winning_regions: List[OCRRegion] = []
        for cluster in clusters:
            best_region = max(cluster, key=lambda r: r.confidence)
            winning_regions.append(OCRRegion(
                text=best_region.text,
                confidence=best_region.confidence,
                bounding_box=best_region.bounding_box,
                detected_angle_degrees=best_region.detected_angle_degrees,
                cluster_id=best_region.cluster_id,
                reading_order_confidence=best_region.reading_order_confidence
            ))

        # Apply reading order resolver
        resolved_regions = self.reading_order_resolver.resolve(winning_regions)

        merged_lines = [r.text for r in resolved_regions if r.text.strip()]
        merged_raw_text = "\n".join(merged_lines)
        merged_confidences = [r.confidence for r in resolved_regions]
        merged_avg_conf = (
            sum(merged_confidences) / len(merged_confidences)
            if merged_confidences else 0.0
        )

        ref_width = frame_ocr_results[0].image_width if frame_ocr_results else 1000
        ref_height = frame_ocr_results[0].image_height if frame_ocr_results else 1000

        return OCRResult(
            raw_text=merged_raw_text,
            regions=resolved_regions,
            average_confidence=round(merged_avg_conf, 3),
            preprocessing_applied=["video_frame_fusion"],
            image_width=ref_width,
            image_height=ref_height
        )
