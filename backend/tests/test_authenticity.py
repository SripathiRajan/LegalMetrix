import cv2
import pytest
import numpy as np
from pathlib import Path

from app.models.extracted_product import AuthenticityResult, AuthenticityVerdict
from app.vision.authenticity import AuthenticityChecker


@pytest.fixture
def synthetic_product_image():
    """Generates a synthetic 200x300 RGB product packaging image."""
    img = np.zeros((300, 200, 3), dtype=np.uint8)
    # Background in blue
    img[:, :] = (200, 50, 50)
    # Header in yellow
    img[10:60, 20:180] = (50, 220, 220)
    # Logo box in white
    img[80:150, 50:150] = (255, 255, 255)
    return img


# 1. Test Lazy Init and Fallback Mode
def test_authenticity_lazy_fallback(synthetic_product_image, tmp_path):
    checker = AuthenticityChecker(reference_dir=tmp_path)

    # In test environment (without DINOv2 weights loaded), must run safely without crashing
    full_emb, logo_emb, palette, ratio = checker.compute_embedding(
        synthetic_product_image,
        logo_bbox=[50, 80, 150, 150]
    )

    assert isinstance(full_emb, np.ndarray)
    assert full_emb.shape == (768,)
    assert isinstance(logo_emb, np.ndarray)
    assert logo_emb.shape == (768,)
    assert len(palette) == 5
    assert all(len(c) == 3 for c in palette)
    assert ratio is not None
    assert 0.0 < ratio < 1.0


# 2. Test Color Palette Extraction and Similarity Math
def test_color_palette_similarity():
    palette_a = [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255], [0, 0, 0]]
    palette_b = [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255], [0, 0, 0]]

    # Identical palettes must yield 1.0
    sim_identical = AuthenticityChecker.compute_color_similarity(palette_a, palette_b)
    assert sim_identical == 1.0

    # Inverted / completely different palette
    palette_c = [[0, 0, 0], [10, 10, 10], [20, 20, 20], [30, 30, 30], [40, 40, 40]]
    palette_d = [[250, 250, 250], [240, 240, 240], [230, 230, 230], [220, 220, 220], [210, 210, 210]]
    sim_diff = AuthenticityChecker.compute_color_similarity(palette_c, palette_d)
    assert sim_diff < 0.5


# 3. Test Brand Packaging Verification (Genuine vs Suspicious vs No Reference)
def test_brand_authenticity_verification(synthetic_product_image, tmp_path, monkeypatch):
    checker = AuthenticityChecker(reference_dir=tmp_path, default_threshold=0.85)

    # Controlled deterministic embeddings for mock testing
    ref_vector = np.zeros(768, dtype=np.float32)
    ref_vector[0] = 1.0  # Unit vector along dimension 0

    genuine_vector = np.zeros(768, dtype=np.float32)
    genuine_vector[0] = 0.95
    genuine_vector[1] = 0.05
    genuine_vector /= np.linalg.norm(genuine_vector)  # Cosine similarity > 0.90

    counterfeit_vector = np.zeros(768, dtype=np.float32)
    counterfeit_vector[10] = 1.0  # Orthogonal vector, cosine similarity = 0.0

    # Save reference brand directly
    ref_file = tmp_path / "tata_salt.npy"
    np.save(ref_file, {
        "brand_id": "tata_salt",
        "brand_name": "Tata Salt",
        "embedding": ref_vector,
        "palette": [[200, 50, 50], [50, 220, 220], [255, 255, 255], [0, 0, 0], [128, 128, 128]],
        "font_height_ratio": 0.23
    }, allow_pickle=True)

    # Case A: Genuine sample
    monkeypatch.setattr(checker, "_extract_dinov2_features", lambda img: genuine_vector)
    res_genuine = checker.compare_to_reference(synthetic_product_image, brand_id="tata_salt")

    assert isinstance(res_genuine, AuthenticityResult)
    assert res_genuine.verdict == AuthenticityVerdict.GENUINE_LIKELY
    assert res_genuine.similarity_score >= 0.85
    assert res_genuine.brand_name == "Tata Salt"
    assert "aligns" in res_genuine.notes.lower()

    # Case B: Counterfeit / Suspicious sample
    monkeypatch.setattr(checker, "_extract_dinov2_features", lambda img: counterfeit_vector)
    res_counterfeit = checker.compare_to_reference(synthetic_product_image, brand_id="tata_salt")

    assert res_counterfeit.verdict == AuthenticityVerdict.SUSPICIOUS
    assert res_counterfeit.similarity_score < 0.85
    assert "counterfeit" in res_counterfeit.notes.lower() or "diverges" in res_counterfeit.notes.lower()

    # Case C: No reference available
    res_missing = checker.compare_to_reference(synthetic_product_image, brand_id="unregistered_brand")
    assert res_missing.verdict == AuthenticityVerdict.NO_REFERENCE_AVAILABLE
    assert res_missing.similarity_score == 0.0
    assert "no verified reference" in res_missing.notes.lower()


# 4. Test Registration and Retrieval from File
def test_save_and_load_reference_brand(synthetic_product_image, tmp_path):
    checker = AuthenticityChecker(reference_dir=tmp_path)

    saved_path = checker.save_reference_brand(
        brand_id="Amul Butter",
        image=synthetic_product_image,
        logo_bbox=[50, 80, 150, 150],
        brand_name="Amul Pasteurised Butter"
    )

    assert saved_path.exists()
    assert saved_path.name == "amul_butter.npy"

    loaded = checker.load_reference_brand("amul_butter")
    assert loaded is not None
    assert loaded["brand_id"] == "amul_butter"
    assert loaded["brand_name"] == "Amul Pasteurised Butter"
    assert loaded["embedding"].shape == (768,)
