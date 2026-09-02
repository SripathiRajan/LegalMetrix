# LegalMetrix: Legal Metrology Compliance Inspection Platform

**Problem Statement 26034**: *Software System to check compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011.*

LegalMetrix is an end-to-end statutory compliance inspection platform engineered for Legal Metrology Officers, Department of Consumer Affairs (DoCA) inspectors, and brand quality assurance teams. It automates OCR declaration extraction, rule-by-rule statutory validation, visual evidence annotation, DINOv2 trade dress authenticity verification, and multi-format audit export generation.

---

## 📋 Compliance with Problem Statement Requirements

| Problem Statement Requirement | System Implementation & Solution Architecture | Status |
|---|---|---|
| **1. Automatic OCR & Declaration Extraction** | Multi-engine OCR ensemble (PaddleOCR + CLAHE preprocessing + heuristic fallback) extracting mandatory declarations: MRP, Net Qty, Dates, Manufacturer, Consumer Care, COO, USP, and Ingredients. | **Fully Implemented** |
| **2. Statutory Rule Engine & Legal Grounding** | Rule engine grounded directly on 40 official DoCA PDFs, PCR 2011, and gazette amendments. Provides exact legal citations, source PDF filenames, and bilingual rule text for every check. | **Fully Implemented** |
| **3. Physical Package & E-Commerce Listing Support** | Dual inspection modes selectable side-by-side: **"Scan Physical Package"** (validates physical font height, PDP placement, declarations) and **"Analyse E-commerce Listing"** (validates digital marketplace declarations, COO filter guidelines). | **Fully Implemented** |
| **4. Visual Bounding Box Evidence & Readability Assessment** | Bounding box normalization, spatial PDP quadrant placement, Laplacian sharpness scoring, and color-coded visual evidence (Green = Pass, Red = Infraction). | **Fully Implemented** |
| **5. Multi-Format Audit Reports (PDF + Editable Formats)** | Generates official PDF Audit Reports (with per-page legal disclaimers and visual evidence) as well as editable formats: Excel (.xlsx with summary, extracted fields, rule results, visual statistics, and legal disclaimer sheets), DOCX Show-Cause Notice Drafts, and CSV. | **Fully Implemented** |
| **6. Inspector Dashboard & Violation Log Repository** | Responsive Web Application with executive compliance gauges, KPI counters, rule-by-rule filtering, historical scan database, brand authenticity tracking, and bulk Excel export. | **Fully Implemented** |
| **7. Statutory Measurement & Screening Disclaimer** | Standardized, automated screening disclaimer enforced across constants, PDF report footers, Excel sheets, DOCX drafts, frontend UI, and API response metadata under Legal Metrology Act, 2009. | **Fully Implemented** |
| **8. Multi-Lingual & DINOv2 Brand Trade Dress Authenticity** | Handles Hindi & English statutory declarations; integrates DINOv2 visual embedding similarity for trade dress authenticity and anti-counterfeiting verification. | **Fully Implemented** |

---

## 🚀 Key Features

### 🏛️ Dual Inspection Modes
- **Scan Physical Package (Default)**: Inspects physical packaged commodity labels, Principal Display Panel (PDP) area ratio, font pixel height, and legibility.
- **Analyse E-Commerce Listing**: Scans online marketplace product listing screenshots to verify statutory e-commerce declarations (Country of Origin, Manufacturer, Net Qty, MRP, Consumer Care) under Rule 6(10) & DoCA advisory guidelines.

### 📄 Multi-Format Audit Exports
1. **PDF Audit Report**: Formal legal report containing annotated evidence image, rule-by-rule table with citations and source PDF filenames, and per-page statutory disclaimers.
2. **Excel (.xlsx) Single Scan**: Multi-sheet workbook (Summary, Extracted Fields, Rule Results, Visual Statistics, and Legal Disclaimer Note sheet).
3. **Excel (.xlsx) Bulk Scans**: Dashboard bulk export containing All Scans, Violations Log, and Legal Disclaimer note sheet.
4. **DOCX Show-Cause Notice Draft**: Editable Word document pre-formatted as a statutory notice under Section 15 & 36 of Legal Metrology Act, 2009 with infraction tables and officer signature blocks.
5. **CSV Export**: Lightweight machine-readable audit record.

---

## 🛠️ Architecture & Tech Stack

- **Backend**: FastAPI, PyTorch, PaddleOCR, OpenCV, ReportLab, openpyxl, python-docx, SQLAlchemy, SQLite, Pydantic.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Recharts.
- **Deployment**: Docker, Docker Compose, Uvicorn, Nginx.

---

## 🔒 Statutory Disclaimer Notice

> *"Font size and readability metrics provided by this system are automated screening estimates based on image resolution and relative text height. They do not constitute statutory physical measurements in millimetres under the Legal Metrology Act, 2009. Final legal determination remains with the authorised Legal Metrology Officer."*

---

## 📜 Footer Notice
*Powered by Official Legal Metrology (Packaged Commodities) Rules, 2011 and amendments issued by Department of Consumer Affairs.*
