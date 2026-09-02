import logging
from typing import Optional, Dict, Any, Tuple, List
from app.models.product import ProductInput, ComplianceResponse
from app.models.extracted_product import (
    OCRResult,
    ExtractedProductData,
    OCRExtractResponse,
    VisionAnalysisResponse,
    AnalyzeResponse,
    AnalyzeVideoResponse,
    SelectedFrameMetadata
)
from app.ocr.preprocessing import ImagePreprocessor
from app.ocr.ocr_engine import BaseOCREngine, PaddleOCREngine
from app.ocr.result_ranker import OCRResultRanker, OCRVariantResult
from app.ocr.ensemble import OCREnsemble, EnsembleResult
from app.vision.reading_order import ReadingOrderResolver
from app.vision.frame_selector import FrameSelector
from app.extraction.declaration_extractor import DeclarationExtractor
from app.vision.evidence import EvidenceAnnotator, EvidenceManager
from app.vision.rectification import ImageRectifier
from app.vision.authenticity import AuthenticityChecker
from app.rules.rule_engine import RuleEngine
from app.services.history_service import HistoryService


logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Application service managing compliance evaluation, multi-pass OCR declaration extraction,
    advanced image rectification, multi-engine ensemble, and computer vision evidence workflows.
    """

    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        ocr_engine: Optional[BaseOCREngine] = None,
        preprocessor: Optional[ImagePreprocessor] = None,
        extractor: Optional[DeclarationExtractor] = None,
        evidence_manager: Optional[EvidenceManager] = None,
        rectifier: Optional[ImageRectifier] = None,
        ranker: Optional[OCRResultRanker] = None,
        ensemble: Optional[OCREnsemble] = None,
        reading_order_resolver: Optional[ReadingOrderResolver] = None,
        frame_selector: Optional[FrameSelector] = None,
        history_service: Optional[HistoryService] = None,
        authenticity_checker: Optional[AuthenticityChecker] = None
    ):
        self.rule_engine = rule_engine or RuleEngine()
        self.ocr_engine = ocr_engine or PaddleOCREngine()
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.evidence_manager = evidence_manager or EvidenceManager()
        self.extractor = extractor or DeclarationExtractor(evidence_manager=self.evidence_manager)
        self.rectifier = rectifier or ImageRectifier()
        self.ranker = ranker or OCRResultRanker()
        self.ensemble = ensemble or OCREnsemble()
        self.reading_order_resolver = reading_order_resolver or ReadingOrderResolver()
        self.frame_selector = frame_selector or FrameSelector(reading_order_resolver=self.reading_order_resolver)
        self.history_service = history_service or HistoryService()
        self.authenticity_checker = authenticity_checker or AuthenticityChecker()



    def check_compliance(self, product: ProductInput) -> ComplianceResponse:
        """
        Direct rule engine evaluation on structured ProductInput.
        """
        return self.rule_engine.evaluate(product)

    def extract_from_image(
        self,
        image_bytes: bytes,
        preprocessing_strategy: str = "standard",
        multi_pass: bool = False,
        use_ensemble: bool = False
    ) -> Tuple[OCRResult, ExtractedProductData, Any, Dict[str, Any]]:
        """
        Runs image preprocessing, optional multi-pass rectification OCR or multi-engine ensemble,
        orientation-aware reading order resolution, and declaration field mapping with visual evidence.
        Returns:
          - OCRResult (selected best variant or resolved ensemble merged result)
          - ExtractedProductData
          - Original decoded BGR image array
          - Multi-pass / ensemble / rectification metadata
        """
        # 1. Preprocessing (returns preprocessed image for OCR and original image for evidence)
        preprocessed_img, original_bgr, operations, scale = self.preprocessor.preprocess_pipeline(
            image_bytes,
            strategy=preprocessing_strategy
        )

        orig_h, orig_w = (original_bgr.shape[:2]) if original_bgr is not None else (1080, 1920)

        # 2. Check for packaging curvature / distortion risk
        curvature_check = self.rectifier.check_curvature_risk(original_bgr)

        if not multi_pass:
            if not use_ensemble:
                # Single-pass standard execution with single engine
                ocr_res = self.ocr_engine.extract_text(preprocessed_img)
                ocr_res.preprocessing_applied = operations
                ocr_res.image_height = orig_h
                ocr_res.image_width = orig_w
                ocr_res.scale_factor = scale

                extracted_data = self.extractor.extract(ocr_res, image_array=original_bgr)
                rect_meta = {
                    "multi_pass_enabled": False,
                    "use_ensemble": False,
                    "strategy_used": preprocessing_strategy,
                    "curvature_check": curvature_check
                }
                return ocr_res, extracted_data, original_bgr, rect_meta

            # Single-pass with Multi-Engine Ensemble + Reading Order Resolver
            ensemble_engine = self.ensemble
            if isinstance(self.ocr_engine, BaseOCREngine) and self.ocr_engine not in ensemble_engine.engines:
                ensemble_engine = OCREnsemble(engines=[self.ocr_engine] + [e for e in ensemble_engine.engines if e != self.ocr_engine])

            ensemble_res = ensemble_engine.process(preprocessed_img)
            merged_ocr = ensemble_res.merged_result.model_copy(deep=True)

            # Pass merged regions through ReadingOrderResolver before declaration extraction
            if merged_ocr.regions:
                ordered_regions = self.reading_order_resolver.resolve(
                    merged_ocr.regions,
                    img_width=orig_w,
                    img_height=orig_h
                )
                merged_ocr.regions = ordered_regions
                merged_ocr.raw_text = "\n".join(r.text for r in ordered_regions)

            merged_ocr.preprocessing_applied = operations
            merged_ocr.image_height = orig_h
            merged_ocr.image_width = orig_w
            merged_ocr.scale_factor = scale

            extracted_data = self.extractor.extract(merged_ocr, image_array=original_bgr)
            rect_meta = {
                "multi_pass_enabled": False,
                "use_ensemble": True,
                "strategy_used": preprocessing_strategy,
                "curvature_check": curvature_check,
                "winning_engine": ensemble_res.winning_engine,
                "engine_agreement_score": ensemble_res.engine_agreement_score,
                "ensemble_metadata": ensemble_res.metadata
            }
            return merged_ocr, extracted_data, original_bgr, rect_meta

        # Multi-Pass OCR with Rectification Variants
        variants = self.rectifier.generate_rectification_variants(image_bytes, include_rotations=True)
        variant_results: List[OCRVariantResult] = []

        for v in variants:
            v_name = v["name"]
            v_img = v["image"]
            if v_img is None:
                continue

            if use_ensemble:
                ensemble_engine = self.ensemble
                if isinstance(self.ocr_engine, BaseOCREngine) and self.ocr_engine not in ensemble_engine.engines:
                    ensemble_engine = OCREnsemble(engines=[self.ocr_engine] + [e for e in ensemble_engine.engines if e != self.ocr_engine])
                ensemble_res = ensemble_engine.process(v_img)
                v_ocr = ensemble_res.merged_result.model_copy(deep=True)
                if v_ocr.regions:
                    v_ocr.regions = self.reading_order_resolver.resolve(v_ocr.regions, img_width=orig_w, img_height=orig_h)
                    v_ocr.raw_text = "\n".join(r.text for r in v_ocr.regions)
            else:
                v_ocr = self.ocr_engine.extract_text(v_img)

            v_ocr.image_height = orig_h
            v_ocr.image_width = orig_w
            v_ocr.scale_factor = scale
            v_ocr.preprocessing_applied = [v_name]

            # Run extraction for scoring
            v_extracted = self.extractor.extract(v_ocr, image_array=original_bgr)
            variant_results.append(OCRVariantResult(
                variant_name=v_name,
                ocr_result=v_ocr,
                extracted_data=v_extracted,
                metadata=v.get("metadata", {})
            ))

        if not variant_results:
            # Fallback if no variants ran
            if use_ensemble:
                ensemble_res = self.ensemble.process(preprocessed_img)
                ocr_res = ensemble_res.merged_result.model_copy(deep=True)
                if ocr_res.regions:
                    ocr_res.regions = self.reading_order_resolver.resolve(ocr_res.regions, img_width=orig_w, img_height=orig_h)
                    ocr_res.raw_text = "\n".join(r.text for r in ocr_res.regions)
            else:
                ocr_res = self.ocr_engine.extract_text(preprocessed_img)

            ocr_res.preprocessing_applied = operations
            ocr_res.image_height = orig_h
            ocr_res.image_width = orig_w
            ocr_res.scale_factor = scale
            extracted_data = self.extractor.extract(ocr_res, image_array=original_bgr)
            return ocr_res, extracted_data, original_bgr, {"multi_pass_enabled": True, "use_ensemble": use_ensemble, "error": "No variants generated"}

        # Rank variants and select best
        best_variant, ranking_meta = self.ranker.select_best_variant(variant_results)
        best_ocr = best_variant.ocr_result
        best_extracted = best_variant.extracted_data or self.extractor.extract(best_ocr, image_array=original_bgr)

        rect_meta = {
            "multi_pass_enabled": True,
            "use_ensemble": use_ensemble,
            "ranking": ranking_meta,
            "curvature_check": curvature_check
        }

        return best_ocr, best_extracted, original_bgr, rect_meta


    def generate_annotated_image(
        self,
        original_bgr: Any,
        compliance_result: ComplianceResponse,
        extracted_data: ExtractedProductData
    ) -> str:
        """
        Generates a base64-encoded annotated image with color-coded bounding boxes.
        """
        if original_bgr is None:
            return ""

        annotations = []
        for result in compliance_result.results:
            field_name = self.rule_engine.RULE_EVIDENCE_MAP.get(result.rule_id)
            if not field_name:
                continue

            ext_field = getattr(extracted_data, field_name, None)
            if ext_field and ext_field.evidence and ext_field.evidence.bounding_box:
                label_short = result.declaration.split("(")[0].strip()
                annotations.append({
                    "bounding_box": ext_field.evidence.bounding_box,
                    "label": label_short,
                    "status": result.status.value
                })

        _, b64_uri = EvidenceAnnotator.annotate_image(original_bgr, annotations)
        return b64_uri

    def analyze_image_end_to_end(
        self,
        image_bytes: bytes,
        preprocessing_strategy: str = "standard",
        multi_pass: bool = True,
        use_ensemble: bool = False,
        brand_name: Optional[str] = None,
        persist: bool = True,
        officer_id: Optional[int] = None,
        image_path: Optional[str] = None
    ) -> AnalyzeResponse:
        """
        Full end-to-end pipeline:
        Image -> Image Quality / Curvature Check -> Rectification & Multi-Pass OCR -> OCR Result Ranking
        -> Multi-Engine Ensemble & Reading Order -> Declaration Extraction -> Visual Evidence -> Compliance Rules -> DINOv2 Authenticity -> Annotated Evidence Image -> Scan Persistence.
        """
        ocr_res, extracted_data, original_bgr, rect_meta = self.extract_from_image(
            image_bytes,
            preprocessing_strategy=preprocessing_strategy,
            multi_pass=multi_pass,
            use_ensemble=use_ensemble
        )

        # Convert extracted structured data to ProductInput
        product_input = extracted_data.to_product_input(raw_text=ocr_res.raw_text)

        # Evaluate compliance via Rule Engine with visual evidence linking
        compliance_result = self.rule_engine.evaluate(product_input, extracted_data=extracted_data)

        # Generate annotated evidence image
        annotated_b64 = self.generate_annotated_image(original_bgr, compliance_result, extracted_data)
        compliance_result.annotated_image = annotated_b64

        # DINOv2 Visual Authenticity Check if brand_name provided
        authenticity_result = None
        if brand_name:
            try:
                authenticity_result = self.authenticity_checker.compare_to_reference(
                    image=image_bytes,
                    brand_id=brand_name
                )
            except Exception as auth_err:
                logger.warning(f"Authenticity check failed for brand '{brand_name}': {str(auth_err)}")

        # Persist scan audit record if enabled
        scan_record = None
        if persist and self.history_service:
            try:
                scan_record = self.history_service.record_scan(
                    compliance_result=compliance_result,
                    extracted_data=extracted_data,
                    visual_statistics={
                        "average_confidence": ocr_res.average_confidence,
                        "regions_detected": len(ocr_res.regions),
                        "preprocessing_applied": ocr_res.preprocessing_applied,
                        "raw_text_length": len(ocr_res.raw_text),
                        "image_width": ocr_res.image_width,
                        "image_height": ocr_res.image_height,
                        "multi_pass_metadata": rect_meta
                    },
                    authenticity_result=authenticity_result,
                    image_path=image_path,
                    officer_id=officer_id
                )
            except Exception as e:
                logger.warning(f"Failed to persist scan record: {str(e)}")

        visual_evidence = {
            "annotated_image_base64": annotated_b64,
            "original_dimensions": [ocr_res.image_height, ocr_res.image_width],
            "bounding_boxes": [],
            "evidence_statistics": {
                "total_declarations_found": len(ocr_res.regions),
                "average_ocr_confidence": ocr_res.average_confidence,
                "obscured_declarations_count": 0
            }
        }

        return AnalyzeResponse(
            extracted_data=extracted_data,
            compliance_result=compliance_result,
            ocr_summary={
                "average_confidence": ocr_res.average_confidence,
                "regions_detected": len(ocr_res.regions),
                "preprocessing_applied": ocr_res.preprocessing_applied,
                "raw_text_length": len(ocr_res.raw_text),
                "image_width": ocr_res.image_width,
                "image_height": ocr_res.image_height,
                "strategy_used": preprocessing_strategy,
                "multi_pass_metadata": rect_meta
            },
            annotated_image=annotated_b64,
            scan_id=scan_record.id if scan_record else None,
            authenticity_result=authenticity_result,
            visual_evidence=visual_evidence
        )

    def analyze_video_end_to_end(
        self,
        video_bytes: bytes,
        max_frames: int = 3,
        use_ensemble: bool = False,
        persist: bool = True,
        officer_id: Optional[int] = None,
        image_path: Optional[str] = None
    ) -> AnalyzeVideoResponse:
        """
        Video Inspection Pipeline:
        1. FrameSelector samples video and extracts top max_frames sharpest keyframes.
        2. Runs OCR (single or ensemble) across all selected frames.
        3. Merges multi-frame OCR regions with IoU > 0.5 consensus (highest confidence wins).
        4. Extracts statutory declarations and evaluates compliance under PCR 2011.
        5. Annotates the primary keyframe with evidence bounding boxes and persists audit scan.
        """
        keyframes = self.frame_selector.extract_keyframes(video_bytes, max_frames=max_frames)
        if not keyframes:
            raise ValueError("No valid keyframes could be extracted from the video stream.")

        frame_ocr_results: List[OCRResult] = []
        frames_metadata: List[SelectedFrameMetadata] = []

        for kf in keyframes:
            if kf.image_array is None:
                continue

            # Run OCR on this frame
            if use_ensemble:
                ens_res = self.ensemble.process(kf.image_array)
                frame_res = ens_res.merged_result
            else:
                # Standard preprocessed OCR extraction
                gray = self.preprocessor.to_grayscale(kf.image_array)
                prep_img = self.preprocessor.enhance_contrast(gray)
                frame_res = self.ocr_engine.extract_text(prep_img)
                frame_res.preprocessing_applied = ["grayscale", "clahe_contrast"]


            frame_ocr_results.append(frame_res)
            frames_metadata.append(SelectedFrameMetadata(
                frame_index=kf.frame_index,
                timestamp_seconds=kf.timestamp_seconds,
                sharpness_score=kf.sharpness_score,
                regions_detected=len(frame_res.regions)
            ))

        # Merge OCR regions across candidate frames
        merged_ocr_res = self.frame_selector.merge_multi_frame_ocr(frame_ocr_results)

        # Extract declarations from merged OCR result
        extracted_data = self.extractor.extract(merged_ocr_res)
        product_input = extracted_data.to_product_input(raw_text=merged_ocr_res.raw_text)

        # Evaluate compliance rules
        compliance_result = self.rule_engine.evaluate(product_input, extracted_data=extracted_data)

        # Annotate highest-sharpness keyframe
        best_frame = max(keyframes, key=lambda f: f.sharpness_score)
        annotated_b64 = self.generate_annotated_image(best_frame.image_array, compliance_result, extracted_data)
        compliance_result.annotated_image = annotated_b64

        # Persist scan audit record if enabled
        if persist and self.history_service:
            try:
                self.history_service.record_scan(
                    compliance_result=compliance_result,
                    extracted_data=extracted_data,
                    visual_statistics={
                        "average_confidence": merged_ocr_res.average_confidence,
                        "regions_detected": len(merged_ocr_res.regions),
                        "preprocessing_applied": merged_ocr_res.preprocessing_applied,
                        "raw_text_length": len(merged_ocr_res.raw_text),
                        "total_frames_analyzed": len(keyframes),
                        "selected_frames": [f.model_dump() for f in frames_metadata]
                    },
                    image_path=image_path,
                    officer_id=officer_id
                )
            except Exception as e:
                logger.warning(f"Failed to persist video scan record: {str(e)}")

        return AnalyzeVideoResponse(
            compliance_result=compliance_result,
            selected_frames=frames_metadata,
            ocr_summary={
                "average_confidence": merged_ocr_res.average_confidence,
                "regions_detected": len(merged_ocr_res.regions),
                "total_frames_analyzed": len(keyframes),
                "multi_frame_fusion": True
            },
            annotated_image=annotated_b64,
            extracted_data=extracted_data
        )


