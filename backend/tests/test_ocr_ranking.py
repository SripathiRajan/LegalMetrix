import pytest
from app.models.extracted_product import OCRResult, OCRRegion
from app.ocr.result_ranker import OCRResultRanker, OCRVariantResult


@pytest.fixture
def ranker():
    return OCRResultRanker()


# 1. Test Scoring of High Quality OCR with statutory declarations vs Low Quality / Noise
def test_ocr_scoring_signals(ranker):
    high_quality_ocr = OCRResult(
        raw_text="ABC Biscuits\nManufactured by: ABC Foods Ltd, Madurai, Tamil Nadu 625001\nMRP ₹50.00 incl. of all taxes\nNet Qty: 100 g\nPkd: 06/2026\nConsumer Care: 1800-123-4567\nCountry of Origin: India",
        regions=[OCRRegion(text="ABC Biscuits", confidence=0.98, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]])],
        average_confidence=0.96
    )

    low_quality_ocr = OCRResult(
        raw_text="A8C B!scu1ts\nM R P 5 O\nN e t 1 0 0\n0 6 2 6",
        regions=[OCRRegion(text="A8C B!scu1ts", confidence=0.45, bounding_box=[[0, 0], [10, 0], [10, 10], [0, 10]])],
        average_confidence=0.45
    )

    score_high, breakdown_high = ranker.calculate_score(high_quality_ocr)
    score_low, breakdown_low = ranker.calculate_score(low_quality_ocr)

    assert score_high > 75.0
    assert score_low < 50.0
    assert score_high > score_low
    assert breakdown_high["keyword_score"] > breakdown_low["keyword_score"]
    assert breakdown_high["pattern_score"] > breakdown_low["pattern_score"]


# 2. Test Ranking Variants and Selecting Best Candidate
def test_rank_and_select_best_variant(ranker):
    v1 = OCRVariantResult(
        variant_name="raw",
        ocr_result=OCRResult(
            raw_text="ABC Biscuits\nMRP 50",
            regions=[],
            average_confidence=0.60
        )
    )

    v2 = OCRVariantResult(
        variant_name="deskewed_clahe",
        ocr_result=OCRResult(
            raw_text="ABC Biscuits\nManufactured by: ABC Foods Pvt Ltd, Madurai, Tamil Nadu\nMRP ₹50.00 incl. of all taxes\nNet Qty: 100 g\nPkd: 06/2026\nConsumer Care: 1800-123-4567\nCountry of Origin: India",
            regions=[],
            average_confidence=0.97
        )
    )

    v3 = OCRVariantResult(
        variant_name="rotated_90deg",
        ocr_result=OCRResult(
            raw_text="...unreadable garbage...",
            regions=[],
            average_confidence=0.20
        )
    )

    best_v, meta = ranker.select_best_variant([v1, v2, v3])
    assert best_v.variant_name == "deskewed_clahe"
    assert meta["selected_variant"] == "deskewed_clahe"
    assert meta["best_composite_score"] > 80.0
    assert meta["total_variants_evaluated"] == 3


# 3. Test Multi-Pass Empty / Garbage Handling
def test_empty_ocr_ranking(ranker):
    empty_ocr = OCRResult(raw_text="", regions=[], average_confidence=0.0)
    score, breakdown = ranker.calculate_score(empty_ocr)
    assert score == 0.0
    assert breakdown["confidence_score"] == 0.0


# 4. Test Statutory Declaration Pattern Matching Boost
def test_statutory_pattern_boost(ranker):
    ocr_with_exact_patterns = OCRResult(
        raw_text="Product\nMRP ₹150.00 incl. of all taxes\nNet Quantity: 500 g\nDate of Pkg: 12/2026",
        regions=[],
        average_confidence=0.90
    )

    score, breakdown = ranker.calculate_score(ocr_with_exact_patterns)
    assert breakdown["pattern_score"] == 30.0  # Full 30/30 on MRP, Qty, and Date pattern matching
