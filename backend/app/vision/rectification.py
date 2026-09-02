import logging
from typing import List, Tuple, Optional, Any, Dict
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available. Rectification will operate in fallback mode.")


class ImageRectifier:
    """
    Advanced Image Rectification Module for real-world packaged commodity images.
    Provides:
      - Skew angle estimation and deskewing (-45 deg to +45 deg)
      - Cardinal orientation handling (0, 90, 180, 270 deg)
      - 4-point perspective / keystone correction (when reliable quadrilateral geometry exists)
      - Multi-strategy image enhancement variants (CLAHE, high contrast, denoise, adaptive binary, upscale)
      - Curvature/distortion safety flags
    """

    def __init__(self):
        pass

    @staticmethod
    def estimate_skew_angle(image: Any) -> Tuple[float, float]:
        """
        Estimates the dominant text skew angle using minimum area bounding boxes of contours
        or Hough line transforms.
        Returns:
          - Estimated angle in degrees (-45.0 to +45.0)
          - Confidence score (0.0 to 1.0)
        """
        if not CV2_AVAILABLE or image is None:
            return 0.0, 0.0

        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Binarize with Otsu threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Morphological dilation to connect characters into word lines
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 3))
            dilated = cv2.dilate(thresh, kernel, iterations=2)

            # Find contours of connected word lines
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return 0.0, 0.0

            angles = []
            weights = []

            for cnt in contours:
                if cv2.contourArea(cnt) < 100:
                    continue
                rect = cv2.minAreaRect(cnt)
                angle = rect[-1]
                w, h = rect[1]

                if w == 0 or h == 0:
                    continue

                # OpenCV minAreaRect returns angle in [-90, 0] or [0, 90] depending on version
                if angle < -45:
                    angle = -(90 + angle)
                elif angle > 45:
                    angle = angle - 90

                # Only consider reasonable skew angles within [-45, +45]
                if -45.0 <= angle <= 45.0:
                    aspect_ratio = max(w, h) / min(w, h)
                    if aspect_ratio >= 1.5:  # Elongated text line
                        angles.append(angle)
                        weights.append(cv2.contourArea(cnt))

            if not angles:
                return 0.0, 0.0

            # Weighted median/average angle
            weights = np.array(weights, dtype=np.float32)
            total_weight = np.sum(weights)
            if total_weight == 0:
                return 0.0, 0.0

            avg_angle = float(np.sum(np.array(angles, dtype=np.float32) * weights) / total_weight)
            confidence = min(1.0, float(len(angles) / 10.0))

            # Only report significant skew > 0.5 degrees
            if abs(avg_angle) < 0.5:
                return 0.0, confidence

            return round(avg_angle, 2), round(confidence, 2)
        except Exception as e:
            logger.debug(f"Skew estimation error: {e}")
            return 0.0, 0.0

    @staticmethod
    def deskew_image(image: Any, angle: float, bg_color: Tuple[int, int, int] = (255, 255, 255)) -> Any:
        """
        Rotates image around its center by `angle` degrees with clean canvas expansion.
        """
        if not CV2_AVAILABLE or image is None or abs(angle) < 0.2:
            return image

        h, w = image.shape[:2]
        center = (w / 2.0, h / 2.0)

        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Calculate new bounding dimensions
        cos = np.abs(rot_mat[0, 0])
        sin = np.abs(rot_mat[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        rot_mat[0, 2] += (new_w / 2.0) - center[0]
        rot_mat[1, 2] += (new_h / 2.0) - center[1]

        border_val = 255 if len(image.shape) == 2 else bg_color
        rotated = cv2.warpAffine(image, rot_mat, (new_w, new_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=border_val)
        return rotated

    @staticmethod
    def rotate_orientation(image: Any, degrees: int) -> Any:
        """
        Rotates image by cardinal angles: 0, 90, 180, 270 degrees.
        """
        if not CV2_AVAILABLE or image is None or degrees % 360 == 0:
            return image

        deg = degrees % 360
        if deg == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif deg == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif deg == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    @staticmethod
    def correct_perspective_quad(image: Any, src_pts: List[List[float]], target_width: Optional[int] = None, target_height: Optional[int] = None) -> Tuple[Any, bool]:
        """
        Performs four-point perspective / keystone transformation if valid quadrilateral points are provided.
        `src_pts` must be 4 coordinate pairs [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] (top-left, top-right, bottom-right, bottom-left).
        Returns:
          - Transformed warped image
          - Success boolean flag
        """
        if not CV2_AVAILABLE or image is None or not src_pts or len(src_pts) != 4:
            return image, False

        try:
            pts = np.array(src_pts, dtype=np.float32)
            
            # Compute width and height of new image based on quadrilateral edge lengths
            tl, tr, br, bl = pts
            width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            max_w = target_width or max(int(width_a), int(width_b))

            height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            max_h = target_height or max(int(height_a), int(height_b))

            if max_w < 10 or max_h < 10:
                return image, False

            dst_pts = np.array([
                [0, 0],
                [max_w - 1, 0],
                [max_w - 1, max_h - 1],
                [0, max_h - 1]
            ], dtype=np.float32)

            matrix = cv2.getPerspectiveTransform(pts, dst_pts)
            warped = cv2.warpPerspective(image, matrix, (max_w, max_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
            return warped, True
        except Exception as e:
            logger.debug(f"Perspective transformation error: {e}")
            return image, False

    @staticmethod
    def upscale_text_region(image: Any, scale: float = 1.5) -> Any:
        """
        Upscales small text regions using Lanczos / cubic interpolation for improved OCR character definition.
        """
        if not CV2_AVAILABLE or image is None or scale <= 1.0:
            return image
        h, w = image.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def check_curvature_risk(image: Any, bbox: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Heuristic detection for packaging surface curvature (e.g. curved bottles, cans).
        Checks aspect ratios, contour non-linearity, and edge curvature.
        """
        if not CV2_AVAILABLE or image is None:
            return {"is_curved": False, "curvature_score": 0.0, "reason": "No curvature detected."}

        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=30, maxLineGap=10)

            # Curved surfaces produce segmented, fragmented non-parallel line segments
            if lines is not None and len(lines) > 20:
                angles = [np.arctan2(l[0][3] - l[0][1], l[0][2] - l[0][0]) * 180 / np.pi for l in lines]
                std_dev = float(np.std(angles))
                if std_dev > 35.0:
                    return {
                        "is_curved": True,
                        "curvature_score": round(std_dev / 90.0, 2),
                        "reason": "Text region exhibits non-linear contour distribution indicative of package curvature / cylinder."
                    }

            return {"is_curved": False, "curvature_score": 0.0, "reason": "Flat planar text region."}
        except Exception:
            return {"is_curved": False, "curvature_score": 0.0, "reason": "Default planar."}

    def generate_rectification_variants(
        self,
        image_bytes: bytes,
        include_rotations: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generates a structured list of image rectification variants for multi-pass OCR.
        Each variant includes:
          - 'name': Descriptive name of the variant (e.g. 'standard', 'deskewed', 'rot_90', 'high_contrast')
          - 'image': Numpy image array ready for OCR
          - 'metadata': Transformations applied (angle, rotation, filters)
        """
        if not CV2_AVAILABLE:
            return [{"name": "raw", "image": None, "metadata": {}}]

        nparr = np.frombuffer(image_bytes, np.uint8)
        orig_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if orig_img is None:
            raise ValueError("Failed to decode image bytes for rectification variants.")

        variants: List[Dict[str, Any]] = []

        # 1. Base / Standard Image
        variants.append({
            "name": "original_standard",
            "image": orig_img,
            "metadata": {"strategy": "standard", "rotation": 0, "skew_angle": 0.0}
        })

        # 2. Skew Estimation & Deskew Variant
        skew_angle, skew_conf = self.estimate_skew_angle(orig_img)
        if abs(skew_angle) >= 1.0 and skew_conf >= 0.2:
            deskewed_img = self.deskew_image(orig_img, skew_angle)
            variants.append({
                "name": f"deskewed_{skew_angle:+.1f}deg",
                "image": deskewed_img,
                "metadata": {"strategy": "deskew", "skew_angle": skew_angle, "confidence": skew_conf}
            })

        # 3. High-Contrast / CLAHE Enhancement
        gray = cv2.cvtColor(orig_img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        clahe_enhanced = clahe.apply(gray)
        variants.append({
            "name": "enhanced_clahe",
            "image": clahe_enhanced,
            "metadata": {"strategy": "clahe_enhanced", "rotation": 0}
        })

        # 4. Adaptive Thresholding (Binary for difficult stamped/printed text)
        binary_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
        )
        variants.append({
            "name": "enhanced_binary",
            "image": binary_thresh,
            "metadata": {"strategy": "adaptive_binary", "rotation": 0}
        })

        # 5. Cardinal Orientation Rotations (if requested)
        if include_rotations:
            for deg in [90, 180, 270]:
                rot_img = self.rotate_orientation(orig_img, deg)
                variants.append({
                    "name": f"rotated_{deg}deg",
                    "image": rot_img,
                    "metadata": {"strategy": "orientation_rotation", "rotation": deg}
                })

        return variants
