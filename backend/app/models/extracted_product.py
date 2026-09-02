from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from app.models.product import ProductInput, ComplianceResponse
from app.vision.evidence import VisualEvidence



class OCRRegion(BaseModel):
    """
    Individual text region detected by the OCR engine.
    """
    text: str = Field(..., description="Recognized text string")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from OCR engine between 0.0 and 1.0")
    bounding_box: List[Union[List[float], float]] = Field(
        default_factory=list,
        description="Bounding box coordinates, e.g. [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] or [x1, y1, x2, y2]"
    )
    detected_angle_degrees: Optional[float] = Field(
        default=None,
        description="Estimated rotation angle of the text polygon in degrees"
    )
    cluster_id: Optional[str] = Field(
        default=None,
        description="Logical spatial/quadrant cluster identifier"
    )
    reading_order_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the reading order assignment"
    )



class OCRResult(BaseModel):
    """
    Complete OCR output containing all detected regions, dimensions, and aggregated raw text.
    """
    raw_text: str = Field(..., description="Full concatenated text extracted from image")
    regions: List[OCRRegion] = Field(default_factory=list, description="List of recognized text bounding boxes and confidences")
    average_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Average OCR confidence across regions")
    preprocessing_applied: List[str] = Field(default_factory=list, description="Preprocessing operations applied to image")
    image_width: int = Field(default=0, description="Width of the original image in pixels")
    image_height: int = Field(default=0, description="Height of the original image in pixels")
    scale_factor: float = Field(default=1.0, description="Preprocessing resize scale factor")


class ExtractedField(BaseModel):
    """
    Standard schema for an extracted Legal Metrology declaration field.
    Preserves value, normalized representation, OCR confidence, source text, bounding box evidence, and visual analytics.
    """
    value: Optional[str] = Field(None, description="Extracted declaration value (or normalized string)")
    raw_value: Optional[str] = Field(None, description="Original unnormalized raw text extracted by OCR")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Extraction confidence score (0.0 to 1.0)")
    source_text: Optional[str] = Field(None, description="Exact sentence/snippet from OCR text where declaration was identified")
    bounding_boxes: List[Any] = Field(
        default_factory=list,
        description="Bounding boxes of OCR regions contributing to this extraction"
    )
    is_detected: bool = Field(default=False, description="True if a valid declaration was detected")
    evidence: Optional[VisualEvidence] = Field(
        default=None,
        description="Detailed visual evidence (resolution, normalized bbox, pixel text height, spatial positioning, readability)"
    )


class ExtractedProductData(BaseModel):
    """
    Structured declarations extracted from OCR text with visual evidence.
    """
    product_name: ExtractedField = Field(default_factory=ExtractedField)
    commodity_name: ExtractedField = Field(default_factory=ExtractedField)
    manufacturer_name: ExtractedField = Field(default_factory=ExtractedField)
    manufacturer_address: ExtractedField = Field(default_factory=ExtractedField)
    packer_name: ExtractedField = Field(default_factory=ExtractedField)
    packer_address: ExtractedField = Field(default_factory=ExtractedField)
    importer_name: ExtractedField = Field(default_factory=ExtractedField)
    importer_address: ExtractedField = Field(default_factory=ExtractedField)
    net_quantity: ExtractedField = Field(default_factory=ExtractedField)
    mrp: ExtractedField = Field(default_factory=ExtractedField)
    unit_sale_price: ExtractedField = Field(default_factory=ExtractedField)
    date_declaration: ExtractedField = Field(default_factory=ExtractedField)
    best_before: ExtractedField = Field(default_factory=ExtractedField)
    consumer_care: ExtractedField = Field(default_factory=ExtractedField)
    consumer_care_email: ExtractedField = Field(default_factory=ExtractedField)
    consumer_care_phone: ExtractedField = Field(default_factory=ExtractedField)
    consumer_care_address: ExtractedField = Field(default_factory=ExtractedField)
    country_of_origin: ExtractedField = Field(default_factory=ExtractedField)
    is_imported: bool = Field(default=False, description="Flag if product appears to be imported based on extraction")
    category: str = Field(default="general", description="Inferred category")

    def to_product_input(self, raw_text: Optional[str] = None) -> ProductInput:
        """
        Converts extracted fields into the ProductInput schema required by the Compliance Rule Engine.
        """
        return ProductInput(
            product_name=self.product_name.value,
            generic_name=self.commodity_name.value or self.product_name.value,
            manufacturer_name=self.manufacturer_name.value,
            manufacturer_address=self.manufacturer_address.value,
            packer_name=self.packer_name.value,
            packer_address=self.packer_address.value,
            importer_name=self.importer_name.value,
            importer_address=self.importer_address.value,
            net_quantity=self.net_quantity.value,
            mrp=self.mrp.value,
            unit_sale_price=self.unit_sale_price.value,
            date_declaration=self.date_declaration.value,
            best_before_date=self.best_before.value,
            consumer_care=self.consumer_care.value,
            consumer_care_email=self.consumer_care_email.value,
            consumer_care_phone=self.consumer_care_phone.value,
            consumer_care_address=self.consumer_care_address.value,
            country_of_origin=self.country_of_origin.value,
            is_imported=self.is_imported,
            category=self.category,
            raw_text=raw_text
        )


class OCRExtractResponse(BaseModel):
    """
    Response model for POST /api/ocr/extract
    """
    ocr_text: str
    average_confidence: float
    regions_count: int
    fields: Dict[str, ExtractedField]
    images_processed: int = 1
    field_sources: Dict[str, int] = Field(default_factory=dict)
    per_image_summary: List[Dict[str, Any]] = Field(default_factory=list)


class VisionAnalysisResponse(BaseModel):
    """
    Response model for POST /api/vision/analyze
    """
    image_width: int
    image_height: int
    regions_detected: int
    fields_with_evidence: Dict[str, ExtractedField]
    annotated_image: Optional[str] = None


class AuthenticityVerdict(str, Enum):
    """
    Categorical verdict evaluating brand packaging visual authenticity.
    """
    GENUINE_LIKELY = "GENUINE_LIKELY"
    SUSPICIOUS = "SUSPICIOUS"
    NO_REFERENCE_AVAILABLE = "NO_REFERENCE_AVAILABLE"


class AuthenticityResult(BaseModel):
    """
    Outcome of DINOv2 visual embedding and brand packaging authenticity verification.
    """
    similarity_score: float = Field(..., description="Cosine similarity score against reference brand embedding (0.0 to 1.0)")
    verdict: AuthenticityVerdict = Field(..., description="Authenticity evaluation verdict")
    threshold_used: float = Field(default=0.80, description="Cosine similarity threshold for genuine classification")
    color_similarity: Optional[float] = Field(default=None, description="Dominant color palette similarity score (0.0 to 1.0)")
    notes: str = Field(default="", description="Explanatory diagnosis or mismatch details")
    brand_name: Optional[str] = Field(default=None, description="Brand name evaluated")
    dominant_palette: List[List[int]] = Field(default_factory=list, description="Extracted RGB dominant color palette (k=5)")
    font_height_ratio: Optional[float] = Field(default=None, description="Logo/text relative height ratio")


class AnalyzeResponse(BaseModel):
    """
    Response model for POST /api/analyze (Full pipeline end-to-end with visual evidence)
    """
    extracted_data: ExtractedProductData
    compliance_result: ComplianceResponse
    ocr_summary: Dict[str, Any]
    annotated_image: Optional[str] = None
    annotated_images: List[str] = Field(default_factory=list)
    scan_id: Optional[int] = None
    authenticity_result: Optional[AuthenticityResult] = None
    visual_evidence: Optional[Dict[str, Any]] = None
    images_processed: int = 1
    field_sources: Dict[str, int] = Field(default_factory=dict)
    per_image_summary: List[Dict[str, Any]] = Field(default_factory=list)



class SelectedFrameMetadata(BaseModel):
    """
    Diagnostic metadata for an analyzed video keyframe.
    """
    frame_index: int
    timestamp_seconds: float
    sharpness_score: float
    regions_detected: int = 0


class AnalyzeVideoResponse(BaseModel):
    """
    Response model for POST /api/analyze/video
    """
    compliance_result: ComplianceResponse
    selected_frames: List[SelectedFrameMetadata]
    ocr_summary: Dict[str, Any]
    annotated_image: Optional[str] = None
    extracted_data: ExtractedProductData


