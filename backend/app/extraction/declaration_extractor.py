import re
import logging
from typing import List, Optional, Tuple, Dict, Any

from app.models.extracted_product import ExtractedField, ExtractedProductData, OCRResult, OCRRegion
from app.vision.evidence import EvidenceManager
from app.extraction.patterns import (
    MRP_PATTERNS,
    QUANTITY_PATTERNS,
    USP_PATTERNS,
    DATE_PATTERNS,
    BEST_BEFORE_PATTERNS,
    MANUFACTURER_KEYWORDS,
    PACKER_KEYWORDS,
    IMPORTER_KEYWORDS,
    CONSUMER_CARE_KEYWORDS,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    ORIGIN_PATTERNS
)
from app.extraction.normalizer import FieldNormalizer

logger = logging.getLogger(__name__)


class DeclarationExtractor:
    """
    Hybrid declaration extractor combining regex, keyword-matching,
    spatial/contextual OCR line parsing, and visual evidence construction.
    """

    def __init__(self, evidence_manager: Optional[EvidenceManager] = None):
        self.normalizer = FieldNormalizer()
        self.evidence_manager = evidence_manager or EvidenceManager()

    def extract(self, ocr_result: OCRResult, image_array: Optional[Any] = None) -> ExtractedProductData:
        """
        Main extraction entry point converting OCRResult into ExtractedProductData with VisualEvidence.
        """
        raw_text = ocr_result.raw_text
        regions = ocr_result.regions
        img_w = ocr_result.image_width or (image_array.shape[1] if image_array is not None else 1920)
        img_h = ocr_result.image_height or (image_array.shape[0] if image_array is not None else 1080)
        scale = ocr_result.scale_factor or 1.0

        # Split text into lines/segments for context analysis
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        extracted = ExtractedProductData()

        # 1. Extract MRP
        extracted.mrp = self._extract_mrp(lines, regions, img_w, img_h, image_array, scale)

        # 2. Extract Net Quantity
        extracted.net_quantity = self._extract_quantity(lines, regions, img_w, img_h, image_array, scale)

        # 3. Extract Unit Sale Price
        extracted.unit_sale_price = self._extract_usp(lines, regions, img_w, img_h, image_array, scale)

        # 4. Extract Dates (Manufacturing / Packing & Expiry)
        extracted.date_declaration, extracted.best_before = self._extract_dates(lines, regions, img_w, img_h, image_array, scale)

        # 5. Extract Manufacturer / Packer / Importer
        mfg_name, mfg_addr = self._extract_entity_info(lines, regions, MANUFACTURER_KEYWORDS, "Manufacturer", img_w, img_h, image_array, scale)
        extracted.manufacturer_name = mfg_name
        extracted.manufacturer_address = mfg_addr

        packer_name, packer_addr = self._extract_entity_info(lines, regions, PACKER_KEYWORDS, "Packer", img_w, img_h, image_array, scale)
        extracted.packer_name = packer_name
        extracted.packer_address = packer_addr

        imp_name, imp_addr = self._extract_entity_info(lines, regions, IMPORTER_KEYWORDS, "Importer", img_w, img_h, image_array, scale)
        extracted.importer_name = imp_name
        extracted.importer_address = imp_addr

        # 6. Extract Consumer Care
        extracted.consumer_care, extracted.consumer_care_email, extracted.consumer_care_phone, extracted.consumer_care_address = self._extract_consumer_care(lines, regions, img_w, img_h, image_array, scale)

        # 7. Extract Country of Origin
        extracted.country_of_origin, is_imported = self._extract_origin(lines, regions, img_w, img_h, image_array, scale)
        extracted.is_imported = is_imported or extracted.importer_name.is_detected

        # 8. Extract Commodity / Product Name
        extracted.product_name, extracted.commodity_name = self._extract_product_name(lines, regions, extracted, img_w, img_h, image_array, scale)

        # Inferred Category
        extracted.category = self._infer_category(raw_text)

        return extracted

    def _find_region_evidence(self, query: str, regions: List[OCRRegion]) -> Tuple[float, List[Any]]:
        """Finds OCR confidence and bounding boxes for matching text regions."""
        if not query or not regions:
            return 0.85, []

        query_clean = query.lower()
        matched_boxes = []
        confidences = []

        for r in regions:
            r_text = r.text.lower()
            if query_clean in r_text or r_text in query_clean:
                matched_boxes.append(r.bounding_box)
                confidences.append(r.confidence)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.80
        return avg_conf, matched_boxes

    def _create_field_with_evidence(
        self,
        value: Optional[str],
        raw_value: Optional[str],
        confidence: float,
        source_text: Optional[str],
        bounding_boxes: List[Any],
        img_w: int,
        img_h: int,
        image_array: Optional[Any],
        scale: float
    ) -> ExtractedField:
        evidence = self.evidence_manager.build_evidence(
            bounding_boxes=bounding_boxes,
            confidence=confidence,
            source_text=source_text,
            img_width=img_w,
            img_height=img_h,
            image_array=image_array,
            scale_factor=scale
        )
        return ExtractedField(
            value=value,
            raw_value=raw_value,
            confidence=confidence,
            source_text=source_text,
            bounding_boxes=bounding_boxes,
            is_detected=True,
            evidence=evidence
        )

    def _extract_mrp(self, lines: List[str], regions: List[OCRRegion], img_w: int, img_h: int, image_array: Optional[Any], scale: float) -> ExtractedField:
        for line in lines:
            for pattern in MRP_PATTERNS:
                match = pattern.search(line)
                if match:
                    raw_val = match.group(0).strip()
                    raw_val = re.sub(r'[a-zA-Z]+$', '', raw_val).strip()
                    line_has_taxes = "incl" in line.lower()
                    target_for_norm = line if line_has_taxes else raw_val
                    normalized_val, num = self.normalizer.normalize_mrp(target_for_norm)
                    if num is not None and num > 0:
                        conf, boxes = self._find_region_evidence(raw_val, regions)
                        return self._create_field_with_evidence(
                            value=normalized_val,
                            raw_value=raw_val,
                            confidence=conf,
                            source_text=line,
                            bounding_boxes=boxes,
                            img_w=img_w,
                            img_h=img_h,
                            image_array=image_array,
                            scale=scale
                        )
        return ExtractedField(is_detected=False)

    def _extract_quantity(self, lines: List[str], regions: List[OCRRegion], img_w: int, img_h: int, image_array: Optional[Any], scale: float) -> ExtractedField:
        for line in lines:
            for pattern in QUANTITY_PATTERNS:
                match = pattern.search(line)
                if match:
                    raw_val = match.group(0).strip()
                    if len(raw_val) > 12 or re.match(r'^(?:1800|19\d{2}|20\d{2})', raw_val):
                        continue
                    normalized_val, num, unit = self.normalizer.normalize_quantity(raw_val)
                    if num is not None and num > 0:
                        conf, boxes = self._find_region_evidence(raw_val, regions)
                        return self._create_field_with_evidence(
                            value=normalized_val,
                            raw_value=raw_val,
                            confidence=conf,
                            source_text=line,
                            bounding_boxes=boxes,
                            img_w=img_w,
                            img_h=img_h,
                            image_array=image_array,
                            scale=scale
                        )
        return ExtractedField(is_detected=False)

    def _extract_usp(self, lines: List[str], regions: List[OCRRegion], img_w: int, img_h: int, image_array: Optional[Any], scale: float) -> ExtractedField:
        for line in lines:
            for pattern in USP_PATTERNS:
                match = pattern.search(line)
                if match:
                    raw_val = match.group(0).strip()
                    conf, boxes = self._find_region_evidence(raw_val, regions)
                    return self._create_field_with_evidence(
                        value=raw_val,
                        raw_value=raw_val,
                        confidence=conf,
                        source_text=line,
                        bounding_boxes=boxes,
                        img_w=img_w,
                        img_h=img_h,
                        image_array=image_array,
                        scale=scale
                    )
        return ExtractedField(is_detected=False)

    def _extract_dates(self, lines: List[str], regions: List[OCRRegion], img_w: int, img_h: int, image_array: Optional[Any], scale: float) -> Tuple[ExtractedField, ExtractedField]:
        date_decl = ExtractedField(is_detected=False)
        best_before = ExtractedField(is_detected=False)

        for line in lines:
            line_clean = line.strip()
            is_mfg_line = any(k in line_clean.lower() for k in MANUFACTURER_KEYWORDS + PACKER_KEYWORDS + IMPORTER_KEYWORDS)

            if not best_before.is_detected:
                for pat in BEST_BEFORE_PATTERNS:
                    m = pat.search(line_clean)
                    if m:
                        raw_val = m.group(0).strip()
                        val_cleaned = self.normalizer.normalize_date(raw_val)
                        conf, boxes = self._find_region_evidence(raw_val, regions)
                        best_before = self._create_field_with_evidence(
                            value=val_cleaned,
                            raw_value=raw_val,
                            confidence=conf,
                            source_text=line_clean,
                            bounding_boxes=boxes,
                            img_w=img_w,
                            img_h=img_h,
                            image_array=image_array,
                            scale=scale
                        )
                        break

            if not date_decl.is_detected:
                for pat in DATE_PATTERNS:
                    m = pat.search(line_clean)
                    if m:
                        raw_val = m.group(0).strip()
                        if is_mfg_line and not any(k in raw_val.lower() for k in ["mfg", "mfd", "pkd", "pkg", "packed", "date"]):
                            continue

                        val_cleaned = self.normalizer.normalize_date(raw_val)
                        conf, boxes = self._find_region_evidence(raw_val, regions)
                        date_decl = self._create_field_with_evidence(
                            value=val_cleaned,
                            raw_value=raw_val,
                            confidence=conf,
                            source_text=line_clean,
                            bounding_boxes=boxes,
                            img_w=img_w,
                            img_h=img_h,
                            image_array=image_array,
                            scale=scale
                        )
                        break

        return date_decl, best_before

    def _extract_entity_info(
        self,
        lines: List[str],
        regions: List[OCRRegion],
        keywords: List[str],
        entity_type: str,
        img_w: int,
        img_h: int,
        image_array: Optional[Any],
        scale: float
    ) -> Tuple[ExtractedField, ExtractedField]:
        name_field = ExtractedField(is_detected=False)
        addr_field = ExtractedField(is_detected=False)

        for i, line in enumerate(lines):
            line_lower = line.lower()
            for kw in keywords:
                if kw in line_lower:
                    remainder = re.split(rf'{kw}[:\-\s]*', line, flags=re.IGNORECASE)[-1].strip()
                    collected_lines = []
                    if remainder:
                        collected_lines.append(remainder)
                    
                    for next_line in lines[i+1 : i+4]:
                        next_lower = next_line.lower()
                        if any(k in next_lower for k in MANUFACTURER_KEYWORDS + PACKER_KEYWORDS + IMPORTER_KEYWORDS + CONSUMER_CARE_KEYWORDS + ["net wt", "net qty", "mrp", "pkd", "mfd", "date of"]):
                            break
                        collected_lines.append(next_line)

                    if collected_lines:
                        full_entity_text = ", ".join(collected_lines)
                        parts = [p.strip() for p in full_entity_text.split(",") if p.strip()]
                        
                        entity_name = parts[0] if parts else full_entity_text
                        entity_addr = ", ".join(parts[1:]) if len(parts) > 1 else full_entity_text

                        conf, boxes = self._find_region_evidence(kw, regions)
                        name_field = self._create_field_with_evidence(
                            value=entity_name,
                            raw_value=full_entity_text,
                            confidence=conf,
                            source_text=line,
                            bounding_boxes=boxes,
                            img_w=img_w,
                            img_h=img_h,
                            image_array=image_array,
                            scale=scale
                        )
                        addr_field = self._create_field_with_evidence(
                            value=entity_addr,
                            raw_value=full_entity_text,
                            confidence=conf,
                            source_text=line,
                            bounding_boxes=boxes,
                            img_w=img_w,
                            img_h=img_h,
                            image_array=image_array,
                            scale=scale
                        )
                        return name_field, addr_field

        return name_field, addr_field

    def _extract_consumer_care(
        self,
        lines: List[str],
        regions: List[OCRRegion],
        img_w: int,
        img_h: int,
        image_array: Optional[Any],
        scale: float
    ) -> Tuple[ExtractedField, ExtractedField, ExtractedField, ExtractedField]:
        care_field = ExtractedField(is_detected=False)
        email_field = ExtractedField(is_detected=False)
        phone_field = ExtractedField(is_detected=False)
        addr_field = ExtractedField(is_detected=False)

        all_text = " \n ".join(lines)

        # 1. Search email
        email_match = EMAIL_PATTERN.search(all_text)
        if email_match:
            email_val = email_match.group(0).strip()
            conf, boxes = self._find_region_evidence(email_val, regions)
            email_field = self._create_field_with_evidence(
                value=email_val,
                raw_value=email_val,
                confidence=conf,
                source_text=email_val,
                bounding_boxes=boxes,
                img_w=img_w,
                img_h=img_h,
                image_array=image_array,
                scale=scale
            )

        # 2. Search phone / helpline
        phone_match = PHONE_PATTERN.search(all_text)
        if phone_match:
            phone_val = phone_match.group(0).strip()
            conf, boxes = self._find_region_evidence(phone_val, regions)
            phone_field = self._create_field_with_evidence(
                value=phone_val,
                raw_value=phone_val,
                confidence=conf,
                source_text=phone_val,
                bounding_boxes=boxes,
                img_w=img_w,
                img_h=img_h,
                image_array=image_array,
                scale=scale
            )

        # 3. Contextual consumer care paragraph
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(kw in line_lower for kw in CONSUMER_CARE_KEYWORDS):
                care_lines = [line]
                for next_line in lines[i+1 : i+3]:
                    if any(k in next_line.lower() for k in ["country of origin", "made in", "mrp", "net wt"]):
                        break
                    care_lines.append(next_line)
                care_text = " ".join(care_lines)
                conf, boxes = self._find_region_evidence("care", regions)
                care_field = self._create_field_with_evidence(
                    value=care_text,
                    raw_value=care_text,
                    confidence=conf,
                    source_text=line,
                    bounding_boxes=boxes,
                    img_w=img_w,
                    img_h=img_h,
                    image_array=image_array,
                    scale=scale
                )
                break

        if not care_field.is_detected and (email_field.is_detected or phone_field.is_detected):
            parts = []
            if phone_field.is_detected:
                parts.append(phone_field.value)
            if email_field.is_detected:
                parts.append(email_field.value)
            combined = " | ".join(parts)
            care_field = self._create_field_with_evidence(
                value=combined,
                raw_value=combined,
                confidence=max(email_field.confidence, phone_field.confidence),
                source_text=combined,
                bounding_boxes=email_field.bounding_boxes + phone_field.bounding_boxes,
                img_w=img_w,
                img_h=img_h,
                image_array=image_array,
                scale=scale
            )

        return care_field, email_field, phone_field, addr_field

    def _extract_origin(self, lines: List[str], regions: List[OCRRegion], img_w: int, img_h: int, image_array: Optional[Any], scale: float) -> Tuple[ExtractedField, bool]:
        for line in lines:
            for pat in ORIGIN_PATTERNS:
                match = pat.search(line)
                if match:
                    raw_val = match.group(1).strip()
                    norm_val = self.normalizer.normalize_country(raw_val)
                    is_imported = norm_val.lower() not in ["india", "in", "ind"]
                    conf, boxes = self._find_region_evidence(raw_val, regions)
                    field = self._create_field_with_evidence(
                        value=norm_val,
                        raw_value=raw_val,
                        confidence=conf,
                        source_text=line,
                        bounding_boxes=boxes,
                        img_w=img_w,
                        img_h=img_h,
                        image_array=image_array,
                        scale=scale
                    )
                    return field, is_imported
        return ExtractedField(is_detected=False), False

    def _extract_product_name(
        self,
        lines: List[str],
        regions: List[OCRRegion],
        extracted_so_far: ExtractedProductData,
        img_w: int,
        img_h: int,
        image_array: Optional[Any],
        scale: float
    ) -> Tuple[ExtractedField, ExtractedField]:
        candidates: List[Tuple[str, int]] = []

        # Scan top lines (up to 6 lines) for commodity name candidates
        for i, line in enumerate(lines[:6]):
            line_clean = line.strip()
            if len(line_clean) > 2 and not any(kw in line_clean.lower() for kw in MANUFACTURER_KEYWORDS + PACKER_KEYWORDS + IMPORTER_KEYWORDS + CONSUMER_CARE_KEYWORDS + ["mrp", "net wt", "net qty", "mfd", "pkg", "date of", "best before", "unit sale price", "country of origin"]):
                candidates.append((line_clean, i))

        if not candidates:
            return ExtractedField(is_detected=False), ExtractedField(is_detected=False)

        # Prefer non-code-like descriptive names over product codes
        descriptive_candidates = [c for c in candidates if not self.normalizer.is_code_like(c[0])]

        if descriptive_candidates:
            # Pick longest descriptive candidate, breaking ties by earlier line position
            chosen_candidate = max(descriptive_candidates, key=lambda c: (len(c[0]), -c[1]))
            chosen_text = chosen_candidate[0]
        else:
            # Only code-like candidates found
            chosen_text = candidates[0][0]

        conf, boxes = self._find_region_evidence(chosen_text, regions)
        field = self._create_field_with_evidence(
            value=chosen_text,
            raw_value=chosen_text,
            confidence=conf,
            source_text=chosen_text,
            bounding_boxes=boxes,
            img_w=img_w,
            img_h=img_h,
            image_array=image_array,
            scale=scale
        )
        return field, field

    def _infer_category(self, raw_text: str) -> str:
        text_lower = raw_text.lower()
        if any(w in text_lower for w in ["biscuit", "cookie", "food", "snack", "flour", "atta", "rice", "tea", "coffee", "oil", "sugar", "spice", "oats"]):
            return "food"
        if any(w in text_lower for w in ["cream", "soap", "lotion", "shampoo", "cosmetic", "perfume"]):
            return "cosmetics"
        if any(w in text_lower for w in ["tablet", "capsule", "syrup", "pharma", "mg", "medicine"]):
            return "pharmaceutical"
        return "general"
