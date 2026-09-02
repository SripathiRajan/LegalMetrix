import logging
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, status, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models.product import ProductInput, ComplianceResponse
from app.models.extracted_product import (
    OCRExtractResponse,
    VisionAnalysisResponse,
    AnalyzeResponse
)
from app.services.compliance_service import ComplianceService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Legal Metrology Compliance & OCR Vision API",
    description="Automated OCR, Advanced Image Rectification, Multi-Pass Selection, Computer Vision Evidence, and Rule Engine pipeline under Legal Metrology (Packaged Commodities) Rules, 2011 (Problem Statement 26034).",
    version="1.0.0"
)

# Enable CORS for standard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

compliance_service = ComplianceService()


@app.get("/", tags=["Health"])
def health_check():
    return {
        "service": "Legal Metrology Compliance Rule Engine & Multi-Pass Vision Pipeline",
        "status": "active",
        "legal_basis": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "version": "1.0.0",
        "ocr_engine": "PaddleOCR (Modular)",
        "vision_module": "BBox Geometry, Spatial Placement, Readability, Skew Rectification & Multi-Pass Ranking"
    }


@app.post(
    "/api/compliance/check",
    response_model=ComplianceResponse,
    status_code=status.HTTP_200_OK,
    tags=["Compliance Engine"],
    summary="Evaluate Packaged Commodity Legal Metrology Compliance directly from structured JSON",
    description="Accepts structured product declarations extracted from OCR/NLP and assesses compliance against individual LMPC Rules."
)
def evaluate_compliance(product: ProductInput):
    try:
        assessment = compliance_service.check_compliance(product)
        return assessment
    except Exception as e:
        logger.error(f"Error evaluating compliance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance evaluation failed: {str(e)}"
        )


@app.post(
    "/api/ocr/extract",
    response_model=OCRExtractResponse,
    status_code=status.HTTP_200_OK,
    tags=["OCR Pipeline"],
    summary="Extract Declarations from Product Image (Multi-Pass Supported)",
    description="Accepts an image upload, executes optional multi-pass rectification and OCR result ranking, and extracts structured Legal Metrology fields."
)
async def extract_declarations_from_image(
    file: UploadFile = File(..., description="Product label image (JPEG, PNG, WEBP)"),
    preprocessing_strategy: str = Query("standard", description="Strategy: standard, denoise, high_contrast, binary, raw"),
    multi_pass: bool = Query(False, description="Enable multi-pass rectification and candidate ranking")
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Please upload a valid image file (JPEG, PNG, etc.)."
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file received."
            )

        ocr_res, extracted, _, _ = compliance_service.extract_from_image(
            contents,
            preprocessing_strategy=preprocessing_strategy,
            multi_pass=multi_pass
        )

        fields_dict = {
            "product_name": extracted.product_name,
            "commodity_name": extracted.commodity_name,
            "manufacturer_name": extracted.manufacturer_name,
            "manufacturer_address": extracted.manufacturer_address,
            "packer_name": extracted.packer_name,
            "packer_address": extracted.packer_address,
            "importer_name": extracted.importer_name,
            "importer_address": extracted.importer_address,
            "net_quantity": extracted.net_quantity,
            "mrp": extracted.mrp,
            "unit_sale_price": extracted.unit_sale_price,
            "date_declaration": extracted.date_declaration,
            "best_before": extracted.best_before,
            "consumer_care": extracted.consumer_care,
            "consumer_care_email": extracted.consumer_care_email,
            "consumer_care_phone": extracted.consumer_care_phone,
            "consumer_care_address": extracted.consumer_care_address,
            "country_of_origin": extracted.country_of_origin,
        }

        return OCRExtractResponse(
            ocr_text=ocr_res.raw_text,
            average_confidence=ocr_res.average_confidence,
            regions_count=len(ocr_res.regions),
            fields=fields_dict
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format or unreadable image: {str(ve)}"
        )
    except Exception as e:
        logger.error(f"Error during OCR extraction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR extraction failed: {str(e)}"
        )


@app.post(
    "/api/vision/analyze",
    response_model=VisionAnalysisResponse,
    status_code=status.HTTP_200_OK,
    tags=["Vision & Spatial Evidence"],
    summary="Analyze Visual Evidence, Readability, and Spatial Placement",
    description="Accepts product image and returns pixel dimensions, spatial positioning, heuristic readability metrics, and annotated image."
)
async def analyze_vision_evidence(
    file: UploadFile = File(..., description="Product label image"),
    preprocessing_strategy: str = Query("standard", description="Strategy: standard, denoise, high_contrast, binary, raw"),
    multi_pass: bool = Query(False, description="Enable multi-pass rectification")
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Please upload an image file."
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file received."
            )

        ocr_res, extracted, original_bgr, _ = compliance_service.extract_from_image(
            contents,
            preprocessing_strategy=preprocessing_strategy,
            multi_pass=multi_pass
        )

        product_input = extracted.to_product_input(raw_text=ocr_res.raw_text)
        compliance_result = compliance_service.rule_engine.evaluate(product_input, extracted_data=extracted)
        annotated_b64 = compliance_service.generate_annotated_image(original_bgr, compliance_result, extracted)

        fields_dict = {
            "product_name": extracted.product_name,
            "commodity_name": extracted.commodity_name,
            "manufacturer_name": extracted.manufacturer_name,
            "manufacturer_address": extracted.manufacturer_address,
            "net_quantity": extracted.net_quantity,
            "mrp": extracted.mrp,
            "date_declaration": extracted.date_declaration,
            "best_before": extracted.best_before,
            "consumer_care": extracted.consumer_care,
            "country_of_origin": extracted.country_of_origin,
        }

        return VisionAnalysisResponse(
            image_width=ocr_res.image_width,
            image_height=ocr_res.image_height,
            regions_detected=len(ocr_res.regions),
            fields_with_evidence=fields_dict,
            annotated_image=annotated_b64
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format or unreadable image: {str(ve)}"
        )
    except Exception as e:
        logger.error(f"Error during vision analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision analysis failed: {str(e)}"
        )


@app.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    tags=["End-to-End Analysis"],
    summary="End-to-End: Product Image -> Multi-Pass Rectification -> OCR -> Extraction -> Visual Evidence -> Compliance Verification",
    description="Processes uploaded image through quality check, image rectification variants, multi-pass OCR ranking, declaration extraction, spatial/readability vision analysis, compliance rule verification, and annotated evidence generation."
)
async def analyze_product_image(
    file: UploadFile = File(..., description="Product label image"),
    preprocessing_strategy: str = Query("standard", description="Strategy: standard, denoise, high_contrast, binary, raw"),
    multi_pass: bool = Query(True, description="Enable multi-pass image rectification and candidate ranking")
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Please upload an image file."
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file received."
            )

        analysis = compliance_service.analyze_image_end_to_end(
            contents,
            preprocessing_strategy=preprocessing_strategy,
            multi_pass=multi_pass
        )
        return analysis
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format or unreadable image: {str(ve)}"
        )
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image compliance analysis failed: {str(e)}"
        )
