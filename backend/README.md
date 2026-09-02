# Legal Metrology Compliance Rule Engine & Computer Vision Evidence Pipeline

Problem Statement 26034: *Software System to check compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011.*

This backend system implements a modular, declarative Legal Metrology compliance rule engine, PaddleOCR declaration extraction pipeline, and Computer Vision Evidence & Readability analysis built with FastAPI, OpenCV, and Pydantic.

---

## 🏛️ Legal Source of Truth & Grounding on Official DoCA Dataset

The compliance rule engine is **grounded directly on the official Department of Consumer Affairs (DoCA) Legal Metrology dataset** (`DOWNLOAD PACK`). This dataset contains authentic Packaged Commodities Rules 2011, amendments, notifications, guidelines, advisories, and SOPs (bilingual Hindi-English).

Every rule in `rules.json` is cross-referenced with exact citations, source PDF filenames, English/Hindi snippets, amendment dates, and category applicability notes:

| Rule ID | Declaration | Official Legal Reference | Source PDF Document | Last Amended | Mandatory / Conditional |
|---|---|---|---|---|---|
| `LMPC_RULE_6_1_A` | Name & Address of Manufacturer / Packer | Rule 6(1)(a) read with Rule 6(1)(ab) | `8(i)_0_1732860957.pdf` | 2023.10.06 | Mandatory |
| `LMPC_RULE_6_1_B` | Generic or Common Name of Commodity | Rule 6(1)(b) | `8(i)_0_1732860957.pdf` | 2021.11.02 | Mandatory |
| `LMPC_RULE_6_1_C` | Net Quantity & Standard Units | Rule 6(1)(c) read with Rule 11, 12, 13 & Schedule II | `2023.12.29 Standard Operating Procedure for Edible oil & Fats...pdf` | 2023.12.29 | Mandatory |
| `LMPC_RULE_6_1_D` | Month & Year of Manufacture / Packing | Rule 6(1)(d) | `2023.01.27 amendment in amendment of 2023 PCR...pdf` | 2023.01.27 | Mandatory |
| `LMPC_RULE_6_1_DA_ORIGIN` | Country of Origin | Rule 6(1)(da) & E-Commerce COO Guidelines | `2026.02.13 PCR 1st COO Filter on e-commerce websites...pdf` | 2026.02.13 | Conditional (Imported / E-commerce) |
| `LMPC_RULE_6_1_DA_IMPORTER` | Name & Address of Importer | Rule 6(1)(da) read with Rule 6(1)(a) | `8(i)_0_1732860957.pdf` | 2022.07.14 | Conditional (Imported goods) |
| `LMPC_RULE_6_1_E` | Maximum Retail Price (MRP incl. of all taxes) | Rule 6(1)(e) read with Rule 2(m) | `2023.7.10 Medical Devices revision of prices...pdf` | 2023.07.10 | Mandatory |
| `LMPC_RULE_6_1_G` | Consumer Care Details (Name, Phone, Email, Addr) | Rule 6(1)(g) read with Rule 6(8) | `8(i)_0_1732860957.pdf` | 2021.11.02 | Mandatory |
| `LMPC_RULE_6_1_F` | Best Before / Use By Date | Rule 6(1)(f) | `2nd PCR Pan Masala_1764736734.pdf` | 2023.10.06 | Conditional (Perishables/Food/Cosmetics) |
| `LMPC_RULE_6_1_E_USP` | Unit Sale Price (USP) | Rule 6(1)(e)(ii) & (iii) (as amended) | `2022 3rd amendment in PCR Garments...pdf` | 2022.12.01 | Conditional (Multi-unit/weight) |

### 📚 Ingestion Script & Multilingual Rules Knowledge Base
- **Ingestion Script (`backend/scripts/ingest_official_rules.py`)**: Processes all 40 PDFs recursively from `DOWNLOAD PACK/`, extracts text using PyMuPDF/pdfplumber with RapidOCR fallback for scanned pages, saves clean text to `backend/app/rules/official_source/extracted/`, and generates `backend/app/rules/official_source/rules_index.json`.
- **Knowledge Base (`backend/app/rules/knowledge_base.py`)**: `RulesKnowledgeBase` class provides `semantic_search(query, top_k)` over English and Hindi legal texts using `sentence-transformers` for instant citation and source PDF retrieval.

---

## 📂 Project Structure

```
backend/
├── app/
│   ├── main.py                     # FastAPI application endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── product.py              # Pydantic schemas for compliance engine & visual evidence
│   │   └── extracted_product.py    # Pydantic schemas for OCR regions & extracted fields
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── ocr_engine.py           # Pluggable OCR engine (PaddleOCR & MockOCREngine)
│   │   └── preprocessing.py        # OpenCV image preprocessing pipeline (CLAHE, Denoise, Thresholding)
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── declaration_extractor.py # Hybrid regex, keyword & contextual line extractor with evidence linking
│   │   ├── patterns.py             # Declaration detection patterns
│   │   └── normalizer.py           # Field normalizer preserving legal irregularities
│   ├── vision/
│   │   ├── __init__.py
│   │   ├── bbox_utils.py           # Geometry, validation, normalization & scale transformations
│   │   ├── readability.py          # Heuristic explainable readability analyzer
│   │   ├── spatial_analysis.py     # Placement & quadrant positioning
│   │   └── evidence.py             # Visual evidence models and color-coded annotation generator
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── rule_engine.py          # Modular rule evaluation & scoring engine
│   │   ├── rule_loader.py          # JSON loader for declarative rules
│   │   └── rules.json              # Declarative rules configuration file
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract BaseValidator interface
│   │   ├── mrp_validator.py        # Rule 6(1)(e) MRP & "incl. of all taxes" validation
│   │   ├── quantity_validator.py   # Rule 6(1)(c) & Rule 13 standard SI unit validation
│   │   ├── date_validator.py       # Rule 6(1)(d) & Rule 6(1)(f) month/year & expiry formats
│   │   ├── manufacturer_validator.py # Rule 6(1)(a) & 6(1)(da) manufacturer/importer address completeness
│   │   ├── consumer_care_validator.py # Rule 6(1)(g) & Rule 6(8) multi-channel consumer contacts
│   │   ├── origin_validator.py     # Rule 6(1)(da) Country of origin for imported goods
│   │   └── commodity_validator.py  # Rule 6(1)(b) generic commodity name & Unit Sale Price
│   └── services/
│       ├── __init__.py
│       └── compliance_service.py   # Service layer coordinating OCR, extraction, vision & rule checks
├── tests/
│   ├── __init__.py
│   ├── test_compliance.py          # Pytest unit tests for compliance rule engine
│   ├── test_extraction.py          # Pytest unit tests for field extraction & normalization
│   ├── test_ocr.py                 # Pytest unit tests for preprocessing & OCR endpoints
│   └── test_vision.py              # Pytest unit tests for vision evidence, readability & annotations
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation & Running

### 1. Prerequisites
- Python 3.10+ installed

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Unit Tests (31/31 passing)
```bash
pytest tests/ -v
```

### 4. Start the FastAPI Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API Swagger documentation is available at: `http://localhost:8000/docs`

---

## 🔍 Visual Evidence & Readability Methodology

### 1. Visual Evidence Object
Every extracted declaration contains a structured `VisualEvidence` payload containing:
- `bounding_box`: Exact coordinates in the original image coordinate space `[xmin, ymin, xmax, ymax]`.
- `normalized_bbox`: Coordinates normalized from `0.0` to `1.0` relative to image dimensions.
- `text_height_pixels`: Height of text in original image resolution.
- `ocr_confidence`: OCR engine confidence for this region.
- `readability_status`: Heuristic assessment (`READABLE`, `LOW_READABILITY`, `UNREADABLE`, `REQUIRES_HUMAN_VERIFICATION`).
- `position`: Spatial alignment (`horizontal`: LEFT/CENTER/RIGHT, `vertical`: TOP/MIDDLE/BOTTOM, `quadrant`: TOP_LEFT/TOP_RIGHT/BOTTOM_LEFT/BOTTOM_RIGHT).
- `source_text`: Exact OCR text detected in region.

### 2. Explainable Heuristic Readability Model
The readability model uses explainable engineering thresholds for automated pre-screening:
- **`minimum_ocr_confidence`** = `0.70` (below 0.50 deemed `UNREADABLE`)
- **`minimum_text_height_pixels`** = `12.0px` (below 8.0px deemed `UNREADABLE`)
- **`minimum_sharpness`** = `20.0` (Laplacian variance of local patch)

> **Important Legal Disclaimer**: Readability metrics are automated screening estimates based on image resolution and pixel height. They do **not** represent statutory physical millimeter measurements under the Legal Metrology Act, 2009.

---

## 🔌 API Endpoints

### 1. Direct Compliance Check: `POST /api/compliance/check`
Evaluates structured JSON input directly against Legal Metrology rules.

### 2. Image OCR Declaration Extraction: `POST /api/ocr/extract`
Uploads a package image and returns raw OCR text, bounding boxes, and extracted fields with confidence.

### 3. Vision & Spatial Evidence: `POST /api/vision/analyze`
Uploads a package image and returns spatial placement, readability analysis, and color-coded annotated image.

### 4. Full End-to-End Analysis: `POST /api/analyze`
Processes uploaded image through preprocessing, OCR, declaration extraction, visual evidence linking, compliance rule verification, and annotated evidence generation in a single request.
