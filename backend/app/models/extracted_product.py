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


class VisionAnalysisResponse(BaseModel):
    """
    Response model for POST /api/vision/analyze
    """
    image_width: int
    image_height: int
    regions_detected: int
    fields_with_evidence: Dict[str, ExtractedField]
    annotated_image: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """
    Response model for POST /api/analyze (Full pipeline end-to-end with visual evidence)
    """
    extracted_data: ExtractedProductData
    compliance_result: ComplianceResponse
    ocr_summary: Dict[str, Any]
    annotated_image: Optional[str] = None
