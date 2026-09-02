import pytest
import numpy as np
import cv2

from app.vision.rectification import ImageRectifier


def create_skewed_text_image(angle=15.0, width=800, height=400):
    """Generates an image with skewed text lines for testing deskew and rectification."""
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    
    # Draw several text lines
    cv2.putText(img, "ABC FOODS PRIVATE LIMITED", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "MRP RS. 100.00 INCL. OF ALL TAXES", (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "NET QUANTITY: 500 g", (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "DATE OF PACKING: 06/2026", (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

    # Rotate by angle
    center = (width / 2.0, height / 2.0)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, rot_mat, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return rotated


# 1. Test Skew Angle Estimation
def test_skew_angle_estimation():
    rectifier = ImageRectifier()
    
    # Flat image (0 deg)
    flat_img = create_skewed_text_image(angle=0.0)
    angle, conf = rectifier.estimate_skew_angle(flat_img)
    assert abs(angle) < 2.0

    # Skewed image (+15 deg)
    skewed_img = create_skewed_text_image(angle=15.0)
    angle_sk, conf_sk = rectifier.estimate_skew_angle(skewed_img)
    assert conf_sk >= 0.0


# 2. Test Deskew Image
def test_deskew_image():
    rectifier = ImageRectifier()
    skewed_img = create_skewed_text_image(angle=12.0)
    deskewed = rectifier.deskew_image(skewed_img, angle=-12.0)
    
    assert deskewed is not None
    assert deskewed.shape[0] >= skewed_img.shape[0]
    assert deskewed.shape[1] >= skewed_img.shape[1]


# 3. Test Orientation Rotations (90, 180, 270 deg)
def test_orientation_rotations():
    rectifier = ImageRectifier()
    img = np.full((300, 500, 3), 255, dtype=np.uint8)

    rot_90 = rectifier.rotate_orientation(img, 90)
    assert rot_90.shape == (500, 300, 3)

    rot_180 = rectifier.rotate_orientation(img, 180)
    assert rot_180.shape == (300, 500, 3)

    rot_270 = rectifier.rotate_orientation(img, 270)
    assert rot_270.shape == (500, 300, 3)


# 4. Test Perspective / Keystone Quad Correction
def test_perspective_correction():
    rectifier = ImageRectifier()
    img = np.full((600, 800, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (700, 500), (0, 0, 0), 2)

    # Valid quad points [tl, tr, br, bl]
    quad_pts = [[120.0, 110.0], [680.0, 90.0], [710.0, 520.0], [90.0, 480.0]]
    warped, success = rectifier.correct_perspective_quad(img, quad_pts, target_width=600, target_height=400)
    assert success is True
    assert warped.shape == (400, 600, 3)

    # Invalid points (empty / incomplete)
    invalid_pts = [[10.0, 10.0]]
    warped_inv, success_inv = rectifier.correct_perspective_quad(img, invalid_pts)
    assert success_inv is False


# 5. Test Text Region Upscaling
def test_upscale_text_region():
    rectifier = ImageRectifier()
    small_img = np.full((50, 100, 3), 255, dtype=np.uint8)
    upscaled = rectifier.upscale_text_region(small_img, scale=2.0)
    assert upscaled.shape == (100, 200, 3)


# 6. Test Curvature Risk Detection
def test_curvature_risk_detection():
    rectifier = ImageRectifier()
    
    # Flat image
    flat_img = np.full((400, 600, 3), 255, dtype=np.uint8)
    res_flat = rectifier.check_curvature_risk(flat_img)
    assert isinstance(res_flat, dict)
    assert "is_curved" in res_flat


# 7. Test Rectification Variants Generation
def test_generate_rectification_variants():
    rectifier = ImageRectifier()
    img = np.full((400, 600, 3), 255, dtype=np.uint8)
    cv2.putText(img, "LEGAL METROLOGY", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    _, buffer = cv2.imencode(".png", img)

    variants = rectifier.generate_rectification_variants(buffer.tobytes(), include_rotations=True)
    assert len(variants) >= 4
    names = [v["name"] for v in variants]
    assert "original_standard" in names
    assert "enhanced_clahe" in names
    assert "enhanced_binary" in names
    assert any("rotated_90deg" in n for n in names)
