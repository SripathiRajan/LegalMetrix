import io
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, status, UploadFile, File, Form, Query, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.models.product import ProductInput, ComplianceResponse
from app.models.extracted_product import (
    OCRExtractResponse,
    VisionAnalysisResponse,
    AnalyzeResponse,
    AnalyzeVideoResponse
)

from app.services.compliance_service import ComplianceService
from app.services.stats_service import StatsService
from app.services.pdf_report_generator import PDFReportGenerator
from app.services.export_service import ExportService
from app.constants import FONT_SIZE_DISCLAIMER
from app.rules.knowledge_base import RulesKnowledgeBase
from app.db.session import get_db, engine
from app.db.base import Base
from app.db.models import Officer
from app.auth import (
    auth_router,
    get_current_active_officer,
    ChatbotQueryRequest,
    ChatbotQueryResponse
)
from app.chatbot import (
    GroundedChatbotService,
    ChatRequest,
    ChatResponse
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
    yield

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Legal Metrology Compliance Rule Engine & Vision Evidence API",
    description=(
        "Production-grade compliance verification engine under the Legal Metrology "
        "(Packaged Commodities) Rules, 2011, with Multi-Engine OCR Ensemble, DINOv2 Authenticity Verification, "
        "Persistent Scan History, Analytics Dashboard, and Official PDF Reporting."
    ),
    version="1.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


compliance_service = ComplianceService()
stats_service = StatsService()
pdf_report_generator = PDFReportGenerator()
export_service = ExportService()
knowledge_base = RulesKnowledgeBase()
chatbot_service = GroundedChatbotService(rules_kb=knowledge_base, stats_service=stats_service)

# Register Authentication & Officer Router
app.include_router(auth_router)





@app.get("/", tags=["Health"])
def health_check():
    return {
        "service": "Legal Metrology Compliance Rule Engine & Multi-Pass Vision Pipeline",
        "status": "active",
        "legal_basis": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "version": "1.0.0",
        "ocr_engine": "PaddleOCR (Modular)",
        "vision_module": "BBox Geometry, Spatial Placement, Readability, Skew Rectification & Multi-Pass Ranking",
        "disclaimer": FONT_SIZE_DISCLAIMER
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
    multi_pass: bool = Query(False, description="Enable multi-pass rectification and candidate ranking"),
    use_ensemble: bool = Query(False, description="Enable multi-engine OCR ensemble with orientation-aware reading order")
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
            multi_pass=multi_pass,
            use_ensemble=use_ensemble
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
    multi_pass: bool = Query(False, description="Enable multi-pass rectification"),
    use_ensemble: bool = Query(False, description="Enable multi-engine OCR ensemble with orientation-aware reading order")
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
            multi_pass=multi_pass,
            use_ensemble=use_ensemble
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
    multi_pass: bool = Query(True, description="Enable multi-pass image rectification and candidate ranking"),
    use_ensemble: bool = Query(False, description="Enable multi-engine OCR ensemble with orientation-aware reading order"),
    brand_name: Optional[str] = Query(None, description="Optional brand name for DINOv2 visual authenticity check"),
    persist: bool = Query(True, description="Persist scan audit record to history database"),
    input_type: str = Query("physical_package", description="Scan input mode: 'physical_package' or 'ecommerce_listing'")
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
            multi_pass=multi_pass,
            use_ensemble=use_ensemble,
            brand_name=brand_name,
            persist=persist,
            input_type=input_type
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


@app.post(
    "/api/analyze/video",
    response_model=AnalyzeVideoResponse,
    status_code=status.HTTP_200_OK,
    tags=["Video Stream Inspection"],
    summary="Video Frame Selection & Multi-Frame Consensus Inspection",
    description=(
        "Accepts a recorded package inspection video, scores frame sharpness with Laplacian variance, "
        "selects optimal keyframes, merges multi-frame OCR regions with IoU > 0.5 consensus (highest confidence wins), "
        "and evaluates statutory compliance."
    )
)
async def analyze_video_end_to_end(
    file: UploadFile = File(...),
    max_frames: int = Query(3, ge=1, le=10, description="Maximum sharp keyframes to select and fuse"),
    use_ensemble: bool = Query(False, description="Enable multi-engine OCR ensemble on each frame")
):
    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty video file received."
            )

        video_analysis = compliance_service.analyze_video_end_to_end(
            video_bytes=contents,
            max_frames=max_frames,
            use_ensemble=use_ensemble
        )
        return video_analysis
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video frame analysis error: {str(ve)}"
        )
    except Exception as e:
        logger.error(f"Error analyzing video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video inspection analysis failed: {str(e)}"
        )



@app.post(
    "/api/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    tags=["Legal Assistant Chatbot"],
    summary="Grounded Conversational Legal Assistant",
    description="Conversational interface answering exclusively from official DoCA Legal Metrology rules and persistent database inspection analytics."
)
def chat_with_legal_assistant(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    try:
        return chatbot_service.process_query(
            message=payload.message,
            db=db,
            context=payload.context
        )
    except Exception as e:
        logger.error(f"Chatbot error processing query '{payload.message}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chatbot query processing failed: {str(e)}"
        )


@app.post(
    "/api/chatbot/query",
    response_model=ChatbotQueryResponse,
    status_code=status.HTTP_200_OK,
    tags=["Legal Assistant Chatbot"],
    summary="Semantic Search & Legal Metrology Grounded Chatbot",
    description="Performs semantic retrieval across official Department of Consumer Affairs (DoCA) Packaged Commodities Rules and SOPs."
)
def query_legal_chatbot(
    payload: ChatbotQueryRequest,
    current_officer: Officer = Depends(get_current_active_officer)
):
    try:
        results = knowledge_base.semantic_search(query=payload.query, top_k=payload.top_k)
        return ChatbotQueryResponse(
            query=payload.query,
            results_count=len(results),
            citations=results
        )
    except Exception as e:
        logger.error(f"Error querying legal chatbot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chatbot query failed: {str(e)}"
        )



@app.get(
    "/api/scans",
    status_code=status.HTTP_200_OK,
    tags=["Scan History & Audit"],
    summary="List Historical Scan Records (Filtered & Paginated)",
    description="Returns a paginated list of persistent scan records with optional status, officer, and product name filters."
)
def list_scan_records(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by compliance status (COMPLIANT, NON_COMPLIANT, etc.)"),
    officer_id: Optional[int] = Query(None, description="Filter by inspector / officer ID"),
    product_name: Optional[str] = Query(None, description="Filter by partial product name"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    try:
        return compliance_service.history_service.list_scans(
            status=status_filter,
            officer_id=officer_id,
            product_name=product_name,
            limit=limit,
            offset=offset,
            db=db
        )

    except Exception as e:
        logger.error(f"Error listing scan records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan history: {str(e)}"
        )


@app.get(
    "/api/scans/stats/summary",
    status_code=status.HTTP_200_OK,
    tags=["Scan History & Audit"],
    summary="Get Aggregated Compliance Dashboard Statistics",
    description="Returns aggregate metrics across all historical scans (compliance rate, status distribution, average score)."
)
def get_scan_statistics(
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    try:
        return compliance_service.history_service.get_dashboard_metrics(db=db)
    except Exception as e:
        logger.error(f"Error computing scan statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute dashboard metrics: {str(e)}"
        )


@app.get(
    "/api/scans/export/xlsx",
    status_code=status.HTTP_200_OK,
    tags=["Scan History & Audit"],
    summary="Bulk Export Scans to Excel (.xlsx)",
    description="Streams an aggregated multi-scan Excel spreadsheet with summary KPIs and violation itemization."
)
def export_bulk_scans_xlsx(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by compliance status"),
    officer_id: Optional[int] = Query(None, description="Filter by inspector / officer ID"),
    product_name: Optional[str] = Query(None, description="Filter by partial product name"),
    limit: int = Query(200, ge=1, le=2000, description="Max records to export"),
    offset: int = Query(0, ge=0, description="Record offset"),
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    try:
        records, _ = compliance_service.history_service.repository.list_scans(
            db=db,
            status=status_filter,
            officer_id=officer_id,
            product_name=product_name,
            limit=limit,
            offset=offset
        )

        xlsx_bytes = export_service.generate_bulk_scans_xlsx(records)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="legal_metrology_scans_bulk_{timestamp}.xlsx"'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting bulk scans to Excel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate bulk Excel export: {str(e)}"
        )


@app.get(
    "/api/scans/{scan_id}",
    status_code=status.HTTP_200_OK,
    tags=["Scan History & Audit"],
    summary="Get Specific Scan Record by ID",
    description="Fetches full assessment details, extracted fields, and audit metadata for a specific scan ID."
)
def get_scan_record_by_id(
    scan_id: int,
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    record = compliance_service.history_service.get_scan_by_id(scan_id=scan_id, db=db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan record #{scan_id} not found."
        )

    return {
        "id": record.id,
        "product_name": record.product_name,
        "overall_status": record.overall_status,
        "compliance_score": record.compliance_score,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "image_path": record.image_path,
        "officer_id": record.officer_id,
        "compliance_result": record.compliance_result,
        "authenticity_result": record.authenticity_result,
        "extracted_data": record.extracted_data,
        "visual_statistics": record.visual_statistics
    }


@app.get(
    "/api/stats/dashboard",
    status_code=status.HTTP_200_OK,
    tags=["Dashboard & Analytics"],
    summary="Get Comprehensive Compliance Dashboard Statistics",
    description="Returns full dashboard analytics including violation rates by field, historical violation trends, top non-compliant brands, authenticity flag rates, and font size distributions with optional date filtering."
)
def get_dashboard_statistics(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD or ISO datetime)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD or ISO datetime)"),
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    try:
        return stats_service.get_dashboard_statistics(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error computing dashboard statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate dashboard statistics: {str(e)}"
        )


@app.get(
    "/api/scans/{scan_id}/report.pdf",
    status_code=status.HTTP_200_OK,
    tags=["Scan History & Audit"],
    summary="Download Official PDF Compliance Audit Report",
    description="Generates and streams an official Legal Metrology compliance PDF audit report with citations, source PDFs, annotated evidence, and authenticity metrics."
)
def download_scan_pdf_report(
    scan_id: int,
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    record = compliance_service.history_service.get_scan_by_id(scan_id=scan_id, db=db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan record #{scan_id} not found."
        )

    try:
        pdf_bytes = pdf_report_generator.generate_report(
            compliance_result=record.compliance_result or {},
            scan_id=record.id,
            product_name=record.product_name,
            officer_id=record.officer_id,
            created_at=record.created_at,
            annotated_image_b64=(record.compliance_result or {}).get("annotated_image"),
            authenticity_result=record.authenticity_result,
            visual_statistics=record.visual_statistics,
            extracted_data=record.extracted_data
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="legal_metrology_report_scan_{scan_id}.pdf"'
            }
        )
    except Exception as e:
        logger.error(f"Error generating PDF report for scan #{scan_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF compliance report: {str(e)}"
        )


@app.get(
    "/api/scans/{scan_id}/export/csv",
    status_code=status.HTTP_200_OK,
    tags=["Scan History & Audit"],
    summary="Export Single Scan Record to CSV",
    description="Streams an editable CSV file containing extracted product declarations and rule-by-rule evaluation."
)
def export_scan_csv(
    scan_id: int,
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    record = compliance_service.history_service.get_scan_by_id(scan_id=scan_id, db=db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan record #{scan_id} not found."
        )

    try:
        csv_str = export_service.generate_scan_csv(record)
        return StreamingResponse(
            io.BytesIO(csv_str.encode("utf-8")),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="legal_metrology_scan_{scan_id}.csv"'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting CSV for scan #{scan_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate CSV export: {str(e)}"
        )


@app.get(
    "/api/scans/{scan_id}/export/xlsx",
    status_code=status.HTTP_200_OK,
    tags=["Scan History & Audit"],
    summary="Export Single Scan Record to Formatted Excel (.xlsx)",
    description="Streams a formatted multi-sheet Excel spreadsheet (Summary, Extracted Fields, Rule Results, Visual Statistics)."
)
def export_scan_xlsx(
    scan_id: int,
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    record = compliance_service.history_service.get_scan_by_id(scan_id=scan_id, db=db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan record #{scan_id} not found."
        )

    try:
        xlsx_bytes = export_service.generate_scan_xlsx(record)
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="legal_metrology_scan_{scan_id}.xlsx"'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting Excel for scan #{scan_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Excel export: {str(e)}"
        )


@app.get(
    "/api/scans/{scan_id}/export/docx",
    status_code=status.HTTP_200_OK,
    tags=["Scan History & Audit"],
    summary="Generate Show-Cause Notice Draft (.docx)",
    description="Streams an official statutory Show-Cause Notice draft under Section 15 & 36 of Legal Metrology Act, 2009."
)
def export_scan_docx(
    scan_id: int,
    db: Session = Depends(get_db),
    current_officer: Officer = Depends(get_current_active_officer)
):
    record = compliance_service.history_service.get_scan_by_id(scan_id=scan_id, db=db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan record #{scan_id} not found."
        )

    try:
        officer_name = current_officer.username if current_officer else None
        docx_bytes = export_service.generate_show_cause_docx(record, officer_name=officer_name)
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="show_cause_notice_scan_{scan_id}.docx"'
            }
        )
    except Exception as e:
        logger.error(f"Error generating Show-Cause Notice for scan #{scan_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Show-Cause Notice draft: {str(e)}"
        )




