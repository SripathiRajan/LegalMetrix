import io
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    HRFlowable
)
from PIL import Image as PILImage

from app.rules.rule_loader import RuleLoader
from app.constants import FONT_SIZE_DISCLAIMER

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """
    Generates official Legal Metrology Compliance Audit PDF reports
    including annotated evidence imagery, rule-by-rule citations,
    source DoCA documents, authenticity verification, and statutory disclaimers.
    """

    def __init__(self, rule_loader: Optional[RuleLoader] = None):
        self.rule_loader = rule_loader or RuleLoader()
        self._rules_cache = {r.rule_id: r for r in self.rule_loader.load_rules()}

    def _get_rule_meta(self, rule_id: str) -> Dict[str, str]:
        """Retrieves official legal reference and source PDF document."""
        r = self._rules_cache.get(rule_id)
        if r:
            return {
                "legal_ref": r.official_legal_reference or r.legal_reference,
                "source_pdf": r.source_pdf or "Packaged Commodities Rules, 2011",
                "declaration": r.declaration_name
            }
        return {
            "legal_ref": "Legal Metrology (Packaged Commodities) Rules, 2011",
            "source_pdf": "Official Gazetted Rules",
            "declaration": rule_id
        }

    def _decode_image_for_report(self, image_data: Optional[str], max_width: float = 400, max_height: float = 220) -> Optional[Image]:
        """Decodes base64 data URI or raw base64 string into a ReportLab flowable Image."""
        if not image_data or not isinstance(image_data, str):
            return None

        try:
            # Strip Data URI prefix if present
            if "," in image_data:
                b64_str = image_data.split(",", 1)[1]
            else:
                b64_str = image_data

            img_bytes = base64.b64decode(b64_str)
            pil_img = PILImage.open(io.BytesIO(img_bytes))
            orig_w, orig_h = pil_img.size

            if orig_w == 0 or orig_h == 0:
                return None

            # Calculate proportional scale
            scale = min(max_width / orig_w, max_height / orig_h, 1.0)
            target_w = orig_w * scale
            target_h = orig_h * scale

            img_buffer = io.BytesIO(img_bytes)
            return Image(img_buffer, width=target_w, height=target_h)
        except Exception as e:
            logger.warning(f"Failed to process annotated image for PDF report: {e}")
            return None

    def generate_report(
        self,
        compliance_result: Dict[str, Any],
        scan_id: Optional[Union[int, str]] = None,
        product_name: Optional[str] = None,
        officer_id: Optional[Union[int, str]] = None,
        created_at: Optional[Union[datetime, str]] = None,
        annotated_image_b64: Optional[str] = None,
        authenticity_result: Optional[Dict[str, Any]] = None,
        visual_statistics: Optional[Dict[str, Any]] = None,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Builds and returns a PDF document as bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=50
        )

        styles = getSampleStyleSheet()

        # Custom Palette Styles
        primary_color = colors.HexColor("#0F2942")  # Deep Navy
        secondary_color = colors.HexColor("#334155") # Slate
        accent_blue = colors.HexColor("#1D4ED8")

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=primary_color,
            alignment=1
        )

        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=secondary_color,
            alignment=1
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=primary_color,
            spaceBefore=8,
            spaceAfter=4
        )

        cell_style = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B")
        )

        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=primary_color
        )

        disclaimer_style = ParagraphStyle(
            "DisclaimerStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#475569")
        )

        elements = []

        # 1. Header Banner
        elements.append(Paragraph("MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION", subtitle_style))
        elements.append(Paragraph("DEPARTMENT OF CONSUMER AFFAIRS • LEGAL METROLOGY DIVISION", subtitle_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("OFFICIAL COMPLIANCE AUDIT & EVIDENCE REPORT", title_style))
        elements.append(Paragraph("Under Legal Metrology (Packaged Commodities) Rules, 2011 (as amended)", subtitle_style))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

        # 2. Inspection Metadata & Executive Summary Box
        date_str = (
            created_at.strftime("%d-%b-%Y %H:%M:%S UTC")
            if isinstance(created_at, datetime)
            else (str(created_at) if created_at else datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC"))
        )

        overall_status = compliance_result.get("overall_status", "UNKNOWN")
        compliance_score = float(compliance_result.get("compliance_score", 0.0))
        passed_cnt = compliance_result.get("passed", 0)
        failed_cnt = compliance_result.get("failed", 0)
        warn_cnt = compliance_result.get("warnings", 0)
        total_checks = compliance_result.get("total_checks", 0)

        # Status badge coloring
        if overall_status == "COMPLIANT":
            status_color = colors.HexColor("#059669")
            status_bg = colors.HexColor("#D1FAE5")
        elif "NON_COMPLIANT" in str(overall_status):
            status_color = colors.HexColor("#DC2626")
            status_bg = colors.HexColor("#FEE2E2")
        else:
            status_color = colors.HexColor("#D97706")
            status_bg = colors.HexColor("#FEF3C7")

        meta_data = [
            [
                Paragraph("<b>Audit Scan ID:</b>", cell_bold),
                Paragraph(f"#{scan_id}" if scan_id else "Live Inspection", cell_style),
                Paragraph("<b>Inspection Date:</b>", cell_bold),
                Paragraph(date_str, cell_style)
            ],
            [
                Paragraph("<b>Commodity / Product:</b>", cell_bold),
                Paragraph(product_name or "Unlabeled Pre-packaged Commodity", cell_style),
                Paragraph("<b>Inspector ID:</b>", cell_bold),
                Paragraph(f"Officer #{officer_id}" if officer_id else "Authorized Inspector", cell_style)
            ],
            [
                Paragraph("<b>Overall Status:</b>", cell_bold),
                Paragraph(f"<b><font color='{status_color.hexval()}'>{overall_status}</font></b>", cell_style),
                Paragraph("<b>Compliance Score:</b>", cell_bold),
                Paragraph(f"<b>{compliance_score:.1f}%</b> ({passed_cnt}/{total_checks} checks passed)", cell_style)
            ]
        ]

        meta_table = Table(meta_data, colWidths=[110, 160, 110, 160])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # 3. Visual Annotated Evidence Image (if available)
        image_src = annotated_image_b64 or compliance_result.get("annotated_image")
        flowable_img = self._decode_image_for_report(image_src)
        if flowable_img:
            elements.append(Paragraph("Visual Packaging Evidence & Annotation", section_heading))
            img_table = Table([[flowable_img]], colWidths=[540])
            img_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(img_table)
            elements.append(Spacer(1, 10))

        # 4. Detailed Rule-by-Rule Compliance Table
        elements.append(Paragraph("Rule-by-Rule Statutory Declarations Audit", section_heading))

        table_headers = [
            Paragraph("<b>Rule & Declaration</b>", cell_bold),
            Paragraph("<b>Official Legal Citation & Source Document</b>", cell_bold),
            Paragraph("<b>Status</b>", cell_bold),
            Paragraph("<b>Detected Value / Findings</b>", cell_bold)
        ]

        table_rows = [table_headers]

        results = compliance_result.get("results", [])
        for r in results:
            rule_id = r.get("rule_id", "")
            meta = self._get_rule_meta(rule_id)
            decl_name = r.get("declaration", meta["declaration"])
            status_val = r.get("status", "UNKNOWN")
            det_val = r.get("detected_value") or "Not Detected / Missing"
            reason = r.get("reason", "")

            # Status cell badge formatting
            if status_val == "PASS":
                status_p = Paragraph("<font color='#059669'><b>PASS</b></font>", cell_style)
            elif status_val == "FAIL":
                status_p = Paragraph("<font color='#DC2626'><b>FAIL</b></font>", cell_style)
            elif status_val == "WARNING":
                status_p = Paragraph("<font color='#D97706'><b>WARNING</b></font>", cell_style)
            else:
                status_p = Paragraph(f"<b>{status_val}</b>", cell_style)

            # Rule cell
            rule_p = Paragraph(f"<b>{decl_name}</b><br/><font color='#64748B' size='6.5'>{rule_id}</font>", cell_style)

            # Legal Citation & Source PDF
            legal_p = Paragraph(
                f"<b>{meta['legal_ref']}</b><br/><font color='#475569'><i>Source: {meta['source_pdf']}</i></font>",
                cell_style
            )

            # Findings cell
            findings_p = Paragraph(
                f"<b>Value:</b> {det_val}<br/><font color='#334155'>{reason}</font>",
                cell_style
            )

            table_rows.append([rule_p, legal_p, status_p, findings_p])

        rules_table = Table(table_rows, colWidths=[120, 160, 60, 200])
        rules_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(rules_table)
        elements.append(Spacer(1, 10))

        # 5. Brand Packaging Authenticity Section (if provided)
        if authenticity_result:
            elements.append(Paragraph("Brand Packaging Authenticity & Anti-Counterfeiting Verification", section_heading))
            auth_verdict = authenticity_result.get("verdict", "UNKNOWN")
            auth_sim = authenticity_result.get("similarity_score", 0.0)
            auth_thresh = authenticity_result.get("threshold_used", 0.80)
            auth_notes = authenticity_result.get("notes", "No additional notes")
            auth_brand = authenticity_result.get("brand_name", product_name or "Standard Packaging")

            if auth_verdict == "GENUINE_LIKELY":
                auth_badge = "<font color='#059669'><b>GENUINE LIKELY</b></font>"
            elif auth_verdict == "SUSPICIOUS":
                auth_badge = "<font color='#DC2626'><b>SUSPICIOUS / POTENTIAL COUNTERFEIT</b></font>"
            else:
                auth_badge = "<font color='#D97706'><b>NO REFERENCE BRAND AVAILABLE</b></font>"

            auth_rows = [
                [
                    Paragraph("<b>Reference Brand:</b>", cell_bold),
                    Paragraph(str(auth_brand), cell_style),
                    Paragraph("<b>Verdict:</b>", cell_bold),
                    Paragraph(auth_badge, cell_style)
                ],
                [
                    Paragraph("<b>Visual Embedding Similarity:</b>", cell_bold),
                    Paragraph(f"{(auth_sim * 100):.2f}% (Threshold: {(auth_thresh * 100):.1f}%)", cell_style),
                    Paragraph("<b>Analysis Notes:</b>", cell_bold),
                    Paragraph(str(auth_notes), cell_style)
                ]
            ]
            auth_table = Table(auth_rows, colWidths=[120, 150, 110, 160])
            auth_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(auth_table)
            elements.append(Spacer(1, 10))

        # 6. Official Legal Disclaimer
        elements.append(KeepTogether([
            HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#94A3B8"), spaceAfter=6),
            Paragraph(
                f"<b>Important Legal Disclaimer:</b> {FONT_SIZE_DISCLAIMER}",
                disclaimer_style
            )
        ]))

        def _draw_page_footer(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
            canvas.setLineWidth(0.5)
            canvas.line(36, 42, 612 - 36, 42)

            footer_p_style = ParagraphStyle(
                "PDFFooterDisclaimer",
                fontName="Helvetica",
                fontSize=6.5,
                leading=8,
                textColor=colors.HexColor("#475569")
            )
            footer_text = f"<b>Statutory Disclaimer:</b> {FONT_SIZE_DISCLAIMER}"
            p = Paragraph(footer_text, footer_p_style)
            w, h = p.wrap(540, 36)
            p.drawOn(canvas, 36, 40 - h)
            canvas.restoreState()

        doc.build(elements, onFirstPage=_draw_page_footer, onLaterPages=_draw_page_footer)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data
