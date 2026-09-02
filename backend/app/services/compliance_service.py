import logging
from typing import Optional, Dict, Any, Tuple, List
from app.models.product import ProductInput, ComplianceResponse
from app.models.extracted_product import (
    OCRResult,
    ExtractedProductData,
    OCRExtractResponse,
    VisionAnalysisResponse,
    AnalyzeResponse
)
from app.ocr.preprocessing import ImagePreprocessor
from app.ocr.ocr_engine import BaseOCREngine, PaddleOCREngine
from app.ocr.result_ranker import OCRResultRanker, OCRVariantResult
from app.extraction.declaration_extractor import DeclarationExtractor
from app.vision.evidence import EvidenceAnnotator, EvidenceManager
from app.vision.rectification import ImageRectifier
from app.rules.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Application service managing compliance evaluation, multi-pass OCR declaration extraction,
    advanced image rectification, and computer vision evidence workflows.
    """

    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        ocr_engine: Optional[BaseOCREngine] = None,
        preprocessor: Optional[ImagePreprocessor] = None,
        extractor: Optional[DeclarationExtractor] = None,
        evidence_manager: Optional[EvidenceManager] = None,
        rectifier: Optional[ImageRectifier] = None,
        ranker: Optional[OCRResultRanker] = None
    ):
        self.rule_engine = rule_engine or RuleEngine()
        self.ocr_engine = ocr_engine or PaddleOCREngine()
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.evidence_manager = evidence_manager or EvidenceManager()
        self.extractor = extractor or DeclarationExtractor(evidence_manager=self.evidence_manager)
        self.rectifier = rectifier or ImageRectifier()
        self.ranker = ranker or OCRResultRanker()

    def check_compliance(self, product: ProductInput) -> ComplianceResponse:
        """
        Direct rule engine evaluation on structured ProductInput.
        """
        return self.rule_engine.evaluate(product)

    def extract_from_image(
        self,
        image_bytes: bytes,
        preprocessing_strategy: str = "standard",
        multi_pass: bool = False
    ) -> Tuple[OCRResult, ExtractedProductData, Any, Dict[str, Any]]:
        """
        Runs image preprocessing, optional multi-pass rectification OCR, and declaration field mapping with visual evidence.
        Returns:
          - OCRResult (selected best variant)
          - ExtractedProductData
          - Original decoded BGR image array
          - Multi-pass / rectification metadata
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
            # Single-pass standard execution
            ocr_res = self.ocr_engine.extract_text(preprocessed_img)
            ocr_res.preprocessing_applied = operations
            ocr_res.image_height = orig_h
            ocr_res.image_width = orig_w
            ocr_res.scale_factor = scale

            extracted_data = self.extractor.extract(ocr_res, image_array=original_bgr)
            rect_meta = {
                "multi_pass_enabled": False,
                "strategy_used": preprocessing_strategy,
                "curvature_check": curvature_check
            }
            return ocr_res, extracted_data, original_bgr, rect_meta

        # Multi-Pass OCR with Rectification Variants
        variants = self.rectifier.generate_rectification_variants(image_bytes, include_rotations=True)
        variant_results: List[OCRVariantResult] = []

        for v in variants:
            v_name = v["name"]
            v_img = v["image"]
            if v_img is None:
                continue

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
            ocr_res = self.ocr_engine.extract_text(preprocessed_img)
            ocr_res.preprocessing_applied = operations
            ocr_res.image_height = orig_h
            ocr_res.image_width = orig_w
            ocr_res.scale_factor = scale
            extracted_data = self.extractor.extract(ocr_res, image_array=original_bgr)
            return ocr_res, extracted_data, original_bgr, {"multi_pass_enabled": True, "error": "No variants generated"}

        # Rank variants and select best
        best_variant, ranking_meta = self.ranker.select_best_variant(variant_results)
        best_ocr = best_variant.ocr_result
        best_extracted = best_variant.extracted_data or self.extractor.extract(best_ocr, image_array=original_bgr)

        rect_meta = {
            "multi_pass_enabled": True,
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
        multi_pass: bool = True
    ) -> AnalyzeResponse:
        """
        Full end-to-end pipeline:
        Image -> Image Quality / Curvature Check -> Rectification & Multi-Pass OCR -> OCR Result Ranking
        -> Declaration Extraction -> Visual Evidence -> Compliance Rules -> Annotated Evidence Image.
        """
        ocr_res, extracted_data, original_bgr, rect_meta = self.extract_from_image(
            image_bytes,
            preprocessing_strategy=preprocessing_strategy,
            multi_pass=multi_pass
        )

        # Convert extracted structured data to ProductInput
        product_input = extracted_data.to_product_input(raw_text=ocr_res.raw_text)

        # Evaluate compliance via Rule Engine with visual evidence linking
        compliance_result = self.rule_engine.evaluate(product_input, extracted_data=extracted_data)

        # Generate annotated evidence image
        annotated_b64 = self.generate_annotated_image(original_bgr, compliance_result, extracted_data)
        compliance_result.annotated_image = annotated_b64

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
                "multi_pass_metadata": rect_meta
            },
            annotated_image=annotated_b64
        )
