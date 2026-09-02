#!/usr/bin/env python3
"""
Ingestion script for official Legal Metrology dataset.
Processes every PDF in the DOWNLOAD PACK folder, extracts text using PyMuPDF/pdfplumber
with RapidOCR fallback for scanned pages, saves clean text files, and generates a structured rules index JSON.
"""

import os
import re
import sys
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Tuple

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import numpy as np

# Try importing RapidOCR for scanned page OCR fallback
try:
    from rapidocr_onnxruntime import RapidOCR
    OCR_ENGINE = RapidOCR()
    HAS_OCR = True
except Exception as e:
    OCR_ENGINE = None
    HAS_OCR = False
    print(f"Warning: RapidOCR not available ({e}). Scanned pages will rely on PDF text extraction only.")


def get_dataset_dir() -> Path:
    """Find dataset pack folder from potential candidate paths or CLI argument."""
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return Path(sys.argv[1])

    candidates = [
        Path(r"C:\Users\ELCOT\Downloads\DOWNLOAD PACK\DOWNLOAD PACK"),
        Path(r"c:\Users\ELCOT\Downloads\DOWNLOAD PACK\DOWNLOAD PACK"),
        Path("dataset_pack/DOWNLOAD PACK"),
        Path("DOWNLOAD PACK"),
        Path("../dataset_pack/DOWNLOAD PACK"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not find official Legal Metrology DOWNLOAD PACK folder. "
        "Please provide path as command line argument or place dataset at dataset_pack/DOWNLOAD PACK."
    )


def extract_page_text_ocr(page: fitz.Page, dpi: int = 100) -> str:
    """Extract text from scanned page using RapidOCR fallback."""
    if not HAS_OCR or OCR_ENGINE is None:
        return ""
    try:
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        img = Image.open(io_bytes(img_bytes))
        img_np = np.array(img)
        ocr_result, _ = OCR_ENGINE(img_np)
        if ocr_result:
            return "\n".join([line[1] for line in ocr_result])
    except Exception as err:
        print(f"OCR error on page: {err}")
    return ""


def io_bytes(b: bytes):
    import io
    return io.BytesIO(b)


def is_hindi(text: str) -> bool:
    """Check if text contains Devanagari (Hindi) characters."""
    devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
    return devanagari_count > 20


def detect_language(text: str) -> str:
    has_hi = is_hindi(text)
    has_en = len(re.findall(r'[a-zA-Z]', text)) > 50
    if has_hi and has_en:
        return "Bilingual (Hindi-English)"
    elif has_hi:
        return "Hindi"
    else:
        return "English"


def detect_document_type(filename: str, text: str) -> str:
    fn_lower = filename.lower()
    t_lower = text.lower()
    if "amendment" in fn_lower or "amendment" in t_lower:
        return "Amendment"
    elif "advisory" in fn_lower or "advisory" in t_lower:
        return "Advisory"
    elif "sop" in fn_lower or "standard operating procedure" in t_lower:
        return "SOP"
    elif "corrigendum" in fn_lower or "corrigendum" in t_lower:
        return "Corrigendum"
    elif "guideline" in fn_lower or "guidelines" in t_lower:
        return "Guidelines"
    elif "notification" in fn_lower or "gazette" in t_lower:
        return "Notification"
    else:
        return "Legal Metrology Circular/Rule"


def extract_date(filename: str, text: str) -> str:
    """Extract official date from filename or text."""
    # Check filename patterns (e.g., 2023.01.27, 2022, 2023.7.10)
    fn_date = re.search(r'(\d{4}[\.\-_]\d{1,2}[\.\-_]\d{1,2}|\d{1,2}[\.\-_]\d{1,2}[\.\-_]\d{4})', filename)
    if fn_date:
        return fn_date.group(1).replace('_', '.').replace('-', '.')

    fn_year = re.search(r'(20\d{2})', filename)
    
    # Check text pattern (e.g., Dated: 10.7.2023, Dated 23rd June, 2023)
    text_date = re.search(r'(?:dated|date)[:\s]+(\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]20\d{2})', text, re.IGNORECASE)
    if text_date:
        return text_date.group(1)

    if fn_year:
        return fn_year.group(1)
    return "2011 (as amended)"


def detect_key_topics(text: str, filename: str) -> List[str]:
    """Detect relevant Legal Metrology domains and product categories."""
    combined = (filename + " " + text).lower()
    topics = []
    
    topic_map = {
        "e-commerce": ["e-commerce", "ecommerce", "online", "marketplace", "website"],
        "country_of_origin": ["country of origin", "coo", "imported", "importer"],
        "garments": ["garment", "garments", "textile", "hosiery", "wear", "readymade"],
        "edible_oil": ["edible oil", "fats", "oil", "fat"],
        "medical_devices": ["medical device", "medical devices", "stent", "drug"],
        "pan_masala": ["pan masala", "tobacco", "gutkha"],
        "qr_code": ["qr code", "qr", "quick response", "digital"],
        "unit_sale_price": ["unit sale price", "usp", "per g", "per kg"],
        "mrp_declaration": ["mrp", "maximum retail price", "retail sale price", "tax"],
        "net_quantity": ["net quantity", "standard pack", "weight", "measure"],
        "date_declaration": ["month and year", "pre-packing", "manufacture date"],
        "manufacturer_packer": ["manufacturer", "packer", "address", "name and address"],
        "consumer_care": ["consumer care", "complaint", "helpline", "toll free"]
    }

    for topic, keywords in topic_map.items():
        if any(kw in combined for kw in keywords):
            topics.append(topic)

    if not topics:
        topics.append("general_packaged_commodities")
    return topics


def derive_title(filename: str, text: str) -> str:
    """Derive clean document title."""
    # Look for Subject: ... line in text
    subj_match = re.search(r'Subject[:\s]+([^\n\r]+)', text, re.IGNORECASE)
    if subj_match and len(subj_match.group(1).strip()) > 10:
        clean_subj = subj_match.group(1).strip()
        return clean_subj[:150]

    # Otherwise clean filename
    name = Path(filename).stem
    name = re.sub(r'_\d{8,12}$', '', name)  # Remove trailing timestamp IDs
    name = name.replace('_', ' ').replace('-', ' ')
    return name.strip()


def process_pdf(pdf_path: Path) -> Tuple[str, Dict[str, Any]]:
    """Process a single PDF: extract text (with OCR fallback) and extract metadata."""
    filename = pdf_path.name
    doc = fitz.open(pdf_path)
    full_text_pages = []
    scanned_pages_processed = 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_text = page.get_text().strip()

        # If text is too short, run OCR fallback (up to 10 scanned pages per PDF)
        if len(page_text) < 50 and HAS_OCR:
            if scanned_pages_processed < 10:
                ocr_text = extract_page_text_ocr(page)
                if len(ocr_text) > len(page_text):
                    page_text = ocr_text
                scanned_pages_processed += 1

        if page_text:
            full_text_pages.append(page_text)

    # Fallback to pdfplumber if fitz extracted very little
    full_text = "\n\n".join(full_text_pages).strip()
    if len(full_text) < 50:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                plumber_pages = []
                for p in pdf.pages:
                    txt = p.extract_text()
                    if txt:
                        plumber_pages.append(txt)
                plumber_text = "\n\n".join(plumber_pages).strip()
                if len(plumber_text) > len(full_text):
                    full_text = plumber_text
        except Exception as e:
            print(f"pdfplumber fallback error for {filename}: {e}")

    # Derive metadata
    title = derive_title(filename, full_text)
    date_str = extract_date(filename, full_text)
    doc_type = detect_document_type(filename, full_text)
    lang = detect_language(full_text)
    key_topics = detect_key_topics(full_text, filename)

    metadata = {
        "filename": filename,
        "title": title,
        "date": date_str,
        "document_type": doc_type,
        "language": lang,
        "key_topics": key_topics,
        "char_count": len(full_text),
        "page_count": len(doc)
    }

    return full_text, metadata


def main():
    dataset_dir = get_dataset_dir()
    print(f"Ingesting official Legal Metrology dataset from: {dataset_dir}")

    # Target output paths
    script_dir = Path(__file__).parent.resolve()
    base_rules_dir = script_dir.parent / "app" / "rules" / "official_source"
    extracted_dir = base_rules_dir / "extracted"
    index_file = base_rules_dir / "rules_index.json"

    extracted_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(list(dataset_dir.rglob("*.pdf")))
    print(f"Found {len(pdf_files)} PDF documents to process.")

    documents_index = []

    for idx, pdf_path in enumerate(pdf_files, 1):
        print(f"[{idx}/{len(pdf_files)}] Processing: {pdf_path.name}...", flush=True)
        try:
            full_text, metadata = process_pdf(pdf_path)

            # Save clean extracted text
            txt_filename = pdf_path.stem + ".txt"
            txt_filepath = extracted_dir / txt_filename
            with open(txt_filepath, "w", encoding="utf-8") as f:
                f.write(full_text)

            documents_index.append(metadata)
            print(f"   -> Extracted {metadata['char_count']} chars ({metadata['language']}), Type: {metadata['document_type']}", flush=True)
        except Exception as e:
            print(f"   -> ERROR processing {pdf_path.name}: {e}", flush=True)

    # Save index JSON
    index_data = {
        "dataset_name": "Official DoCA Legal Metrology (Packaged Commodities) Rules & Amendments",
        "total_documents": len(documents_index),
        "documents": documents_index
    }

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully processed {len(documents_index)} files!")
    print(f"Extracted texts saved in: {extracted_dir}")
    print(f"Rules index JSON saved in: {index_file}")


if __name__ == "__main__":
    main()
