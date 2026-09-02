import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.extracted_product import OCRResult, OCRRegion
from app.ocr.ocr_engine import (
    BaseOCREngine,
    PaddleOCREngine,
    EasyOCREngine,
    TesseractOCREngine
)
from app.ocr.result_ranker import OCRResultRanker
from app.vision.bbox_utils import BBoxUtils

logger = logging.getLogger(__name__)


class EnsembleResult(BaseModel):
    """
    Structured outcome of multi-engine OCR ensemble processing.
    """
    primary_result: OCRResult = Field(..., description="Highest-scoring single-engine OCRResult")
    merged_result: OCRResult = Field(..., description="Merged OCRResult with consensus-matched regions")
    winning_engine: str = Field(..., description="Identifier of the winning OCR engine")
    engine_agreement_score: float = Field(..., ge=0.0, le=1.0, description="Agreement metric across engines (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic and explainability metadata")


class OCREnsemble:
    """
    Multi-Engine OCR Ensemble:
      - Runs every successfully initialized engine on the same preprocessed image
      - Evaluates candidate results using OCRResultRanker.calculate_score()
      - Returns the highest-scoring single-engine OCRResult as primary
      - Merges regions across engines using IoU > 0.5 (highest-confidence text wins per matched region)
      - Computes explainable engine_agreement_score (0.0 to 1.0) and winning_engine metadata
    """

    def __init__(
        self,
        engines: Optional[List[BaseOCREngine]] = None,
        iou_threshold: float = 0.5
    ):
        if engines is not None:
            self.engines = engines
        else:
            self.engines = [
                PaddleOCREngine(),
                EasyOCREngine(),
                TesseractOCREngine()
            ]
        self.ranker = OCRResultRanker()
        self.iou_threshold = iou_threshold

    def _get_engine_name(self, engine: BaseOCREngine, index: int) -> str:
        """Returns a readable unique identifier for the engine instance."""
        name = engine.__class__.__name__
        return f"{name}_{index}" if name == "MockOCREngine" else name

    def process(self, image: Any) -> EnsembleResult:
        """
        Executes multi-engine OCR ensemble on the provided image array.
        """
        engine_evaluations: List[Tuple[str, OCRResult, float, Dict[str, float]]] = []

        for idx, engine in enumerate(self.engines):
            engine_name = self._get_engine_name(engine, idx)
            try:
                result = engine.extract_text(image)
                # Check if the engine produced a non-empty result (not an uninitialized fallback)
                if result and (result.raw_text.strip() or len(result.regions) > 0):
                    score, breakdown = self.ranker.calculate_score(result)
                    engine_evaluations.append((engine_name, result, score, breakdown))
                    logger.debug(f"Engine {engine_name} produced score {score} with {len(result.regions)} regions.")
                else:
                    logger.debug(f"Engine {engine_name} produced empty result or was uninitialized.")
            except Exception as e:
                logger.warning(f"Engine {engine_name} failed during extraction: {str(e)}")

        # Case 1: No engine succeeded or all produced empty output
        if not engine_evaluations:
            empty_result = OCRResult(
                raw_text="",
                regions=[],
                average_confidence=0.0,
                preprocessing_applied=[]
            )
            return EnsembleResult(
                primary_result=empty_result,
                merged_result=empty_result,
                winning_engine="None",
                engine_agreement_score=0.0,
                metadata={
                    "winning_engine": "None",
                    "engine_agreement_score": 0.0,
                    "active_engines_count": 0,
                    "warning": "No OCR engines produced valid results"
                }
            )

        # Sort engines descending by composite score, then by average OCR confidence
        ranked_evaluations = sorted(
            engine_evaluations,
            key=lambda x: (x[2], x[1].average_confidence),
            reverse=True
        )

        winning_entry = ranked_evaluations[0]
        winning_engine_name = winning_entry[0]
        primary_result = winning_entry[1]
        winning_score = winning_entry[2]
        winning_breakdown = winning_entry[3]

        num_active = len(ranked_evaluations)

        # Case 2: Only 1 engine active
        if num_active == 1:
            metadata = {
                "winning_engine": winning_engine_name,
                "engine_agreement_score": 1.0,
                "active_engines": [winning_engine_name],
                "active_engines_count": 1,
                "engine_scores": {winning_engine_name: winning_score},
                "total_regions_merged": len(primary_result.regions),
                "clusters_count": len(primary_result.regions),
                "agreed_clusters_count": len(primary_result.regions),
                "scoring_breakdown": winning_breakdown
            }
            return EnsembleResult(
                primary_result=primary_result,
                merged_result=primary_result.model_copy(deep=True),
                winning_engine=winning_engine_name,
                engine_agreement_score=1.0,
                metadata=metadata
            )

        # Case 3: Multiple active engines -> Cluster regions by IoU > threshold and merge
        # Each item in cluster: (engine_name, OCRRegion)
        clusters: List[List[Tuple[str, OCRRegion]]] = []

        for eng_name, ocr_res, _, _ in ranked_evaluations:
            for region in ocr_res.regions:
                best_match_idx = -1
                best_iou = self.iou_threshold

                for c_idx, cluster in enumerate(clusters):
                    # Compare region against all existing regions in this cluster
                    for _, c_region in cluster:
                        iou = BBoxUtils.calculate_iou(region.bounding_box, c_region.bounding_box)
                        if iou > best_iou:
                            best_iou = iou
                            best_match_idx = c_idx

                if best_match_idx >= 0:
                    clusters[best_match_idx].append((eng_name, region))
                else:
                    clusters.append([(eng_name, region)])

        # Determine winning region per cluster (highest confidence wins)
        merged_regions: List[OCRRegion] = []
        agreed_clusters_count = 0

        for cluster in clusters:
            # Highest confidence text wins per matched region
            winning_pair = max(cluster, key=lambda item: item[1].confidence)
            best_region = winning_pair[1]

            # Track unique engines in cluster
            unique_engines_in_cluster = set(item[0] for item in cluster)
            if len(unique_engines_in_cluster) > 1:
                agreed_clusters_count += 1

            merged_regions.append(OCRRegion(
                text=best_region.text,
                confidence=best_region.confidence,
                bounding_box=best_region.bounding_box
            ))

        # Sort merged regions spatially in reading order (top-to-bottom, left-to-right)
        def _spatial_sort_key(region: OCRRegion) -> Tuple[float, float]:
            xyxy = BBoxUtils.to_xyxy(region.bounding_box)
            return (round(xyxy[1], 1), round(xyxy[0], 1))

        merged_regions.sort(key=_spatial_sort_key)

        merged_lines = [r.text for r in merged_regions]
        merged_raw_text = "\n".join(merged_lines)
        merged_confidences = [r.confidence for r in merged_regions]
        merged_avg_conf = (
            sum(merged_confidences) / len(merged_confidences)
            if merged_confidences else 0.0
        )

        merged_result = OCRResult(
            raw_text=merged_raw_text,
            regions=merged_regions,
            average_confidence=round(merged_avg_conf, 3),
            preprocessing_applied=primary_result.preprocessing_applied,
            image_width=primary_result.image_width,
            image_height=primary_result.image_height,
            scale_factor=primary_result.scale_factor
        )

        # Compute engine agreement score (0.0 to 1.0)
        # Fraction of cross-engine consensus across all detected clusters
        if clusters:
            cluster_agreement_ratios = [
                (len(set(item[0] for item in c)) - 1) / (num_active - 1)
                for c in clusters
            ]
            engine_agreement_score = round(
                max(0.0, min(1.0, sum(cluster_agreement_ratios) / len(clusters))),
                4
            )
        else:
            engine_agreement_score = 0.0

        metadata = {
            "winning_engine": winning_engine_name,
            "engine_agreement_score": engine_agreement_score,
            "active_engines": [e[0] for e in ranked_evaluations],
            "active_engines_count": num_active,
            "engine_scores": {e[0]: e[2] for e in ranked_evaluations},
            "total_regions_merged": len(merged_regions),
            "clusters_count": len(clusters),
            "agreed_clusters_count": agreed_clusters_count,
            "scoring_breakdown": winning_breakdown
        }

        return EnsembleResult(
            primary_result=primary_result,
            merged_result=merged_result,
            winning_engine=winning_engine_name,
            engine_agreement_score=engine_agreement_score,
            metadata=metadata
        )

    def extract_text(self, image: Any) -> OCRResult:
        """
        BaseOCREngine-compatible extraction method returning primary OCRResult.
        """
        return self.process(image).primary_result
