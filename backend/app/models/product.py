from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

from app.constants import FONT_SIZE_DISCLAIMER


class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REQUIRES_HUMAN_VERIFICATION = "REQUIRES_HUMAN_VERIFICATION"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class OverallComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    POTENTIALLY_NON_COMPLIANT = "POTENTIALLY_NON_COMPLIANT"
    PARTIAL_COMPLIANCE_NEEDS_REVIEW = "PARTIAL_COMPLIANCE_NEEDS_REVIEW"


class ProductInput(BaseModel):
    """
    Structured product data extracted from OCR/NLP engines or manual entry.
    """
    product_name: Optional[str] = Field(None, description="Name or generic description of the product")
    generic_name: Optional[str] = Field(None, description="Generic/Common name of the commodity")
    manufacturer_name: Optional[str] = Field(None, description="Name of the manufacturer")
    manufacturer_address: Optional[str] = Field(None, description="Complete address of manufacturer")
    packer_name: Optional[str] = Field(None, description="Name of the packer if distinct from manufacturer")
    packer_address: Optional[str] = Field(None, description="Address of packer")
    importer_name: Optional[str] = Field(None, description="Name of the importer for imported products")
    importer_address: Optional[str] = Field(None, description="Address of importer")
    net_quantity: Optional[str] = Field(None, description="Net quantity declaration (e.g., '100 g', '1 L', '10 N')")
    mrp: Optional[str] = Field(None, description="MRP declaration string (e.g., '₹50', 'MRP Rs. 50.00 incl. of all taxes')")
    unit_sale_price: Optional[str] = Field(None, description="Unit sale price (e.g., '₹0.50 / g')")
    date_declaration: Optional[str] = Field(None, description="Date/month/year of manufacture or packing (e.g., '06/2026')")
    best_before_date: Optional[str] = Field(None, description="Best before / Use by date where applicable")
    consumer_care: Optional[str] = Field(None, description="Consumer care contact details or hotline")
    consumer_care_email: Optional[str] = Field(None, description="Consumer care email address")
    consumer_care_phone: Optional[str] = Field(None, description="Consumer care phone / toll free number")
    consumer_care_address: Optional[str] = Field(None, description="Consumer care physical / postal address")
    country_of_origin: Optional[str] = Field(None, description="Country of origin")
    is_imported: Optional[bool] = Field(False, description="Flag whether the product is imported")
    category: Optional[str] = Field("general", description="Product category (e.g., 'food', 'cosmetics', 'pharmaceutical', 'general')")
    package_type: Optional[str] = Field("single_unit", description="Package type: 'single_unit', 'multi_unit', 'combo'")
    raw_text: Optional[str] = Field(None, description="Full raw OCR text for context or fallback verification")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional contextual metadata")


class RuleDefinition(BaseModel):
    rule_id: str
    declaration_name: str
    field_name: str
    mandatory: bool = True
    conditional: bool = False
    applicability_condition: Optional[str] = None
    validation_type: str
    description: str
    legal_reference: str
    severity: SeverityLevel = SeverityLevel.HIGH
    official_legal_reference: Optional[str] = Field(None, description="Exact official citation from DoCA dataset")
    source_pdf: Optional[str] = Field(None, description="Source PDF filename from official DoCA dataset")
    english_text: Optional[str] = Field(None, description="Extracted English legal text excerpt")
    hindi_text_snippet: Optional[str] = Field(None, description="Extracted Hindi legal text excerpt when available")
    last_amended_date: Optional[str] = Field(None, description="Last amended or notification date")
    applicability_notes: Optional[str] = Field(None, description="Category applicability notes (food, e-commerce, etc.)")


class RuleCheckResult(BaseModel):
    rule_id: str
    declaration: str
    status: RuleStatus
    detected_value: Optional[str] = None
    reason: str
    legal_reference: str
    severity: SeverityLevel
    metadata: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Visual & OCR evidence including bounding boxes, source text, confidence, and readability"
    )


class ComplianceResponse(BaseModel):
    overall_status: OverallComplianceStatus
    compliance_score: float = Field(..., ge=0.0, le=100.0, description="Compliance score between 0 and 100")
    total_checks: int
    passed: int
    failed: int
    warnings: int
    human_verification_required: int
    not_applicable: int
    violations: List[RuleCheckResult] = Field(default_factory=list, description="List of failed or warning checks")
    results: List[RuleCheckResult] = Field(default_factory=list, description="Detailed results of all evaluated rules")
    annotated_image: Optional[str] = Field(
        default=None,
        description="Base64 Data URI of original image with color-coded bounding boxes and declaration labels"
    )
    summary: Optional[str] = Field(
        default="Compliance assessment completed.",
        description="Summary explanation of compliance evaluation result"
    )
    input_type: Optional[str] = Field(
        default="physical_package",
        description="Scan input mode: 'physical_package' or 'ecommerce_listing'"
    )
    guidance_note: Optional[str] = Field(
        default=None,
        description="Guidance for inspectors when multiple principal statutory declarations are missing"
    )
    disclaimer: str = Field(
        default=FONT_SIZE_DISCLAIMER,
        description="Legal disclaimer regarding font size and rule-engine automation"
    )
