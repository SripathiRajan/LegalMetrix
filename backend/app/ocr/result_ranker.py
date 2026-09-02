import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.models.extracted_product import OCRResult, ExtractedProductData
from app.extraction.patterns import (
    MRP_PATTERNS,
    QUANTITY_PATTERNS,
    DATE_PATTERNS,
    MANUFACTURER_KEYWORDS,
    CONSUMER_CARE_KEYWORDS,
    ORIGIN_PATTERNS
)

logger = logging.getLogger(__name__)


class OCRVariantResult(BaseModel):
    """
    Result of a single OCR pass across an image rectification/enhancement variant.
    """
    variant_name: str
    ocr_result: OCRResult
    extracted_data: Optional[ExtractedProductData] = None
    composite_score: float = 0.0
    scoring_breakdown: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OCRResultRanker:
    """
    Ranks multiple OCR passes using explainable signals:
      - OCR Confidence score (0.0 to 1.0)
      - Count of meaningful characters and words
      - Statutory declaration keyword presence (Manufacturer, MRP, Net Qty, Pkd/Mfg, Consumer Care, Origin)
      - Valid regex pattern matches for MRP, standard quantities, and dates
      - Agreement across multiple OCR passes
    Selects the strongest consistent OCR extraction without fabricating text or hallucinating declarations.
    """

    # Weights for ranking formula
    CONFIDENCE_WEIGHT = 25.0
    KEYWORD_MATCH_WEIGHT = 35.0
    PATTERN_MATCH_WEIGHT = 30.0
    TEXT_DENSITY_WEIGHT = 10.0

    def __init__(self):
        pass

    def calculate_score(self, ocr_result: OCRResult) -> Tuple[float, Dict[str, float]]:
        """
        Computes an explainable quality score (0.0 - 100.0) for an OCR pass.
        """
        raw_text = ocr_result.raw_text.strip()
        text_lower = raw_text.lower()

        if not raw_text or len(raw_text) < 3:
            return 0.0, {
                "confidence_score": 0.0,
                "keyword_score": 0.0,
                "pattern_score": 0.0,
                "density_score": 0.0
            }

        # 1. OCR Confidence Component (0 - 25 pts)
        avg_conf = ocr_result.average_confidence
        conf_score = avg_conf * self.CONFIDENCE_WEIGHT

        # 2. Statutory Keyword Match Component (0 - 35 pts)
        keyword_hits = 0
        total_keyword_groups = 6

        # Check Manufacturer / Packer
        if any(k in text_lower for k in MANUFACTURER_KEYWORDS + ["packed by", "pkd by", "mfg", "mfd"]):
            keyword_hits += 1

        # Check MRP keywords
        if any(k in text_lower for k in ["mrp", "m.r.p", "max retail price", "maximum retail price", "incl of all taxes", "incl. taxes"]):
            keyword_hits += 1

        # Check Net Quantity keywords
        if any(k in text_lower for k in ["net qty", "net quantity", "net wt", "net weight", "net contents", "100 g", "500 g", "1 kg", "1 l"]):
            keyword_hits += 1

        # Check Dates
        if any(k in text_lower for k in ["pkd", "mfd", "date of", "best before", "use by", "expiry", "exp"]):
            keyword_hits += 1

        # Check Consumer Care
        if any(k in text_lower for k in CONSUMER_CARE_KEYWORDS + ["email", "toll free", "helpline", "care@"]):
            keyword_hits += 1

        # Check Origin
        if any(k in text_lower for k in ["country of origin", "made in", "product of", "india"]):
            keyword_hits += 1

        keyword_score = (keyword_hits / total_keyword_groups) * self.KEYWORD_MATCH_WEIGHT

        # 3. Valid Pattern Match Component (0 - 30 pts)
        pattern_hits = 0
        total_patterns = 3

        # MRP pattern match
        if any(p.search(raw_text) for p in MRP_PATTERNS):
            pattern_hits += 1

        # Quantity pattern match
        if any(p.search(raw_text) for p in QUANTITY_PATTERNS):
            pattern_hits += 1

        # Date pattern match
        if any(p.search(raw_text) for p in DATE_PATTERNS):
            pattern_hits += 1

        pattern_score = (pattern_hits / total_patterns) * self.PATTERN_MATCH_WEIGHT

        # 4. Text Density / Quality (0 - 10 pts)
        # Ratio of alphanumeric characters vs garbage symbols
        words = raw_text.split()
        alnum_chars = sum(1 for c in raw_text if c.isalnum() or c.isspace())
        density_ratio = (alnum_chars / len(raw_text)) if len(raw_text) > 0 else 0.0
        word_count_factor = min(1.0, len(words) / 8.0)
        density_score = (density_ratio * 0.6 + word_count_factor * 0.4) * self.TEXT_DENSITY_WEIGHT

        total_score = round(conf_score + keyword_score + pattern_score + density_score, 2)

        breakdown = {
            "confidence_score": round(conf_score, 2),
            "keyword_score": round(keyword_score, 2),
            "pattern_score": round(pattern_score, 2),
            "density_score": round(density_score, 2)
        }

        return total_score, breakdown

    def rank_variants(self, variant_results: List[OCRVariantResult]) -> List[OCRVariantResult]:
        """
        Scores and ranks a list of OCRVariantResult instances in descending order of quality.
        """
        for v in variant_results:
            score, breakdown = self.calculate_score(v.ocr_result)
            v.composite_score = score
            v.scoring_breakdown = breakdown

        # Sort descending by composite score, then by OCR confidence
        ranked = sorted(
            variant_results,
            key=lambda x: (x.composite_score, x.ocr_result.average_confidence),
            reverse=True
        )
        return ranked

    def select_best_variant(
        self,
        variant_results: List[OCRVariantResult]
    ) -> Tuple[OCRVariantResult, Dict[str, Any]]:
        """
        Picks the best variant from multiple OCR passes and provides explainability metadata.
        """
        if not variant_results:
            raise ValueError("No OCR variant results provided for ranking.")

        ranked = self.rank_variants(variant_results)
        best = ranked[0]

        # Agreement analysis across passes
        variants_evaluated = len(ranked)
        confidence_std = float(np.std([v.ocr_result.average_confidence for v in ranked])) if len(ranked) > 1 else 0.0

        metadata = {
            "selected_variant": best.variant_name,
            "best_composite_score": best.composite_score,
            "best_ocr_confidence": best.ocr_result.average_confidence,
            "confidence_std_dev": round(confidence_std, 3),
            "total_variants_evaluated": variants_evaluated,
            "scoring_breakdown": best.scoring_breakdown,
            "variants_summary": [
                {
                    "name": v.variant_name,
                    "score": v.composite_score,
                    "confidence": v.ocr_result.average_confidence,
                    "text_length": len(v.ocr_result.raw_text)
                }
                for v in ranked
            ]
        }

        return best, metadata
