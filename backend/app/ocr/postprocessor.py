import re
import logging
from typing import List, Dict, Tuple, Optional
from app.models.extracted_product import OCRResult, OCRRegion

logger = logging.getLogger(__name__)


class OCRPostProcessor:
    """
    Post-processing text cleanup and fine-tuning engine optimized for
    Legal Metrology packaging labels. Performs:
    1. OCR confusion pattern corrections (e.g. R5 -> Rs., Pkcl -> Pkd, Ncl -> Net).
    2. Number and date digit repair (e.g. O vs 0, l/I vs 1 in numeric contexts).
    3. Legal Metrology statutory keyword repair via fuzzy / regex patterns.
    4. Unit standardization (e.g. gms -> g, ltrs -> L, kgs -> kg).
    5. Cleaning both overall raw_text and individual OCRRegion texts.
    """

    # Common OCR misread replacement rules (regex pattern, replacement)
    TEXT_REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
        # MRP & Price repairs
        (re.compile(r'\b(?:R5|R\$|M\.?R\.?P\.?R5)\b', re.IGNORECASE), "Rs."),
        (re.compile(r'\bRs(?!\.)\b', re.IGNORECASE), "Rs."),
        (re.compile(r'\bRs\.\.\b', re.IGNORECASE), "Rs."),
        (re.compile(r'\b(?:m\.?r\.?p\.?|mrp)\s*[:\-\.]?\s*r5\b', re.IGNORECASE), "MRP Rs."),
        (re.compile(r'\bRs\.\s*([0-9]+)[oO]\b', re.IGNORECASE), r"Rs. \g<1>0"),  # Trailing O -> 0 in price


        (re.compile(r'\b0/-\b'), "/-"),

        # Net Quantity & Weight repairs
        (re.compile(r'\b(?:Ncl\s*Qty|Net\s*Oty|Net\s*Ouantity|Net\s*Qtv)\b', re.IGNORECASE), "Net Qty"),
        (re.compile(r'\bNcl\b', re.IGNORECASE), "Net"),
        (re.compile(r'\bNet\s*Wt\.?\s*[:\-\.]?', re.IGNORECASE), "Net Wt: "),
        (re.compile(r'\bNet\s*Vol\.?\s*[:\-\.]?', re.IGNORECASE), "Net Vol: "),


        # Date & Packaging repairs
        (re.compile(r'\b(?:Pkcl|Pkl|Pkc|Packd|Pckd|Pkgd)\b', re.IGNORECASE), "Pkd"),
        (re.compile(r'\b(?:Mfd|Mfc|Mfgd|Manufd)\b', re.IGNORECASE), "Mfd"),
        (re.compile(r'\bDate\s*of\s*Packin\b', re.IGNORECASE), "Date of Packing"),
        (re.compile(r'\bBest\s*Befor\b', re.IGNORECASE), "Best Before"),

        # Manufacturer & Consumer Care repairs
        (re.compile(r'\b(?:Mfg\s*by|Mfd\s*by|Manuf\s*by|Manufctured\s*by)\b', re.IGNORECASE), "Manufactured by"),
        (re.compile(r'\b(?:Mktd\s*by|Mktg\s*by|Marketd\s*by)\b', re.IGNORECASE), "Marketed by"),
        (re.compile(r'\b(?:Pkd\s*by|Packed\s*&\s*Mktd\s*by)\b', re.IGNORECASE), "Packed by"),
        (re.compile(r'\b(?:Cust\s*Care|Consumr\s*Care|Customr\s*Care|Customer\s*Svc)\b', re.IGNORECASE), "Consumer Care"),
        (re.compile(r'\bToll\s*Fre\b', re.IGNORECASE), "Toll Free"),
        (re.compile(r'\bContct\s*Us\b', re.IGNORECASE), "Contact Us"),

        # Country of Origin repairs
        (re.compile(r'\b(?:Cntry\s*of\s*Origin|Country\s*of\s*Orgin)\b', re.IGNORECASE), "Country of Origin"),
        (re.compile(r'\bMade\s*in\s*lndia\b', re.IGNORECASE), "Made in India"),
    ]

    # Digit / character fix in numeric contexts (prices, quantities, dates)
    NUMERIC_CONTEXT_REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
        # Fix 'O' or 'o' surrounded by numbers -> '0'
        (re.compile(r'(?<=\d)[oO](?=\d|\b)'), "0"),
        (re.compile(r'(?<=\b)[oO](?=\d)'), "0"),
        # Fix 'l' or 'I' inside digits -> '1'
        (re.compile(r'(?<=\d)[lI](?=\d|\b)'), "1"),
        (re.compile(r'(?<=\b)[lI](?=\d)'), "1"),
        # Fix 'S' or 's' inside numbers like 50 -> 5
        (re.compile(r'(?<=\d)[sS](?=\d)'), "5"),
    ]

    # Unit standardization rules
    UNIT_REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
        (re.compile(r'(\d)\s*(?:gms?\.?|gram|grams)\b', re.IGNORECASE), r"\1 g"),
        (re.compile(r'(\d)\s*(?:kgs?\.?|kilo|kilograms?)\b', re.IGNORECASE), r"\1 kg"),
        (re.compile(r'(\d)\s*(?:ltrs?\.?|liter|liters|litre|litres)\b', re.IGNORECASE), r"\1 L"),
        (re.compile(r'(\d)\s*(?:mls?\.?|milliliter|millilitres)\b', re.IGNORECASE), r"\1 ml"),
        (re.compile(r'(\d)\s*(?:pcs|nos|units|count)\b', re.IGNORECASE), r"\1 N"),
    ]

    def __init__(self):
        pass

    def clean_text_line(self, text: str) -> str:
        """
        Applies cleaning operations to a single line or snippet of OCR text.
        """
        if not text or not text.strip():
            return ""

        cleaned = text.strip()

        # 1. Statutory keyword & confusion replacements
        for pattern, replacement in self.TEXT_REPLACEMENTS:
            cleaned = pattern.sub(replacement, cleaned)

        # 2. Numeric context digit repairs (e.g. prices, quantities, dates)
        if any(char.isdigit() for char in cleaned) or any(k in cleaned.lower() for k in ["mrp", "rs", "net", "pkd", "mfd", "qty", "exp"]):
            for pattern, replacement in self.NUMERIC_CONTEXT_REPLACEMENTS:
                cleaned = pattern.sub(replacement, cleaned)

        # 3. Unit standardization
        for pattern, replacement in self.UNIT_REPLACEMENTS:
            cleaned = pattern.sub(replacement, cleaned)

        # 4. Collapse multiple spaces
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)

        return cleaned.strip()

    def process_ocr_result(self, ocr_result: OCRResult) -> OCRResult:
        """
        Cleans and updates an OCRResult in-place or returns a refined copy.
        Fine-tunes both overall raw_text and individual OCRRegion items.
        """
        if not ocr_result:
            return ocr_result

        cleaned_regions: List[OCRRegion] = []
        cleaned_lines: List[str] = []

        for region in ocr_result.regions:
            orig_text = region.text
            cleaned_t = self.clean_text_line(orig_text)

            if cleaned_t:
                cleaned_regions.append(OCRRegion(
                    text=cleaned_t,
                    confidence=region.confidence,
                    bounding_box=region.bounding_box
                ))
                cleaned_lines.append(cleaned_t)

        # Also clean raw_text directly if regions were empty or missing
        if not cleaned_lines and ocr_result.raw_text:
            lines = ocr_result.raw_text.splitlines()
            cleaned_lines = [self.clean_text_line(l) for l in lines if l.strip()]

        full_raw_text = "\n".join(cleaned_lines)
        preprocessing_list = list(ocr_result.preprocessing_applied or [])
        if "ocr_postprocessed" not in preprocessing_list:
            preprocessing_list.append("ocr_postprocessed")

        return OCRResult(
            raw_text=full_raw_text,
            regions=cleaned_regions if cleaned_regions else ocr_result.regions,
            average_confidence=ocr_result.average_confidence,
            preprocessing_applied=preprocessing_list,
            image_width=ocr_result.image_width,
            image_height=ocr_result.image_height,
            scale_factor=ocr_result.scale_factor
        )
