import logging
from typing import List, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV (cv2) not available. Preprocessing will operate in fallback mode.")


class ImagePreprocessor:
    """
    Modular image preprocessing pipeline using OpenCV.
    Supports multiple selectable strategies without blindly forcing every filter.
    Preserves original and preprocessed dimensions for exact coordinate mapping.
    """

    def __init__(self):
        pass

    def decode_image_bytes(self, image_bytes: bytes) -> Any:
        """Decodes raw image bytes into a numpy image array (BGR format)."""
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV is required to process image bytes.")
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image. Invalid image file or corrupted format.")
        return img

    def resize_image(self, img: Any, max_dim: int = 1920) -> Tuple[Any, float]:
        """Resizes image maintaining aspect ratio if larger than max_dim."""
        h, w = img.shape[:2]
        if max(h, w) <= max_dim:
            return img, 1.0

        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale

    def to_grayscale(self, img: Any) -> Any:
        """Converts BGR image to grayscale."""
        if len(img.shape) == 2:
            return img
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def denoise(self, gray_img: Any, kernel_size: int = 3) -> Any:
        """Gaussian/median noise reduction."""
        return cv2.medianBlur(gray_img, kernel_size)

    def enhance_contrast(self, gray_img: Any, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)) -> Any:
        """Contrast Limited Adaptive Histogram Equalization (CLAHE)."""
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(gray_img)

    def adaptive_threshold(self, gray_img: Any, block_size: int = 15, c: int = 4) -> Any:
        """Applies adaptive Gaussian thresholding for text extraction on uneven lighting."""
        # Ensure block_size is odd
        if block_size % 2 == 0:
            block_size += 1
        return cv2.adaptiveThreshold(
            gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c
        )

    def sharpen(self, gray_img: Any) -> Any:
        """Sharpens image to enhance edge definition of small text characters."""
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]], dtype=np.float32)
        return cv2.filter2D(gray_img, -1, kernel)

    def upscale_image(self, img: Any, factor: float = 2.0) -> Any:
        """Upscales image using bicubic interpolation for small text OCR resolution boost."""
        if not CV2_AVAILABLE:
            return img
        h, w = img.shape[:2]
        new_w, new_h = int(w * factor), int(h * factor)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    def deskew(self, gray_img: Any) -> Tuple[Any, float]:
        """Automatically calculates text skew angle and rotates image straight."""
        if not CV2_AVAILABLE:
            return gray_img, 0.0

        try:
            # Threshold to get dark text on light background or vice versa
            blur = cv2.GaussianBlur(gray_img, (5, 5), 0)
            thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

            # Find coordinates of non-zero pixels
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 50:
                return gray_img, 0.0

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # Only rotate if skew angle is significant (> 0.5 degrees and < 30 degrees)
            if abs(angle) > 0.5 and abs(angle) < 30.0:
                h, w = gray_img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(gray_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated, angle
        except Exception as e:
            logger.debug(f"Deskew calculation bypassed: {e}")

        return gray_img, 0.0

    def preprocess_pipeline(
        self,
        image_bytes: bytes,
        strategy: str = "standard"
    ) -> Tuple[Any, Any, List[str], float]:
        """
        Executes a targeted preprocessing strategy.
        Returns:
          - Preprocessed image (for OCR)
          - Original decoded BGR image (for visual evidence annotation)
          - List of operations applied
          - Scaling factor (preprocessed / original)
        """
        original_bgr = self.decode_image_bytes(image_bytes)
        operations_applied = []

        resized_img, scale = self.resize_image(original_bgr)
        if scale < 1.0:
            operations_applied.append(f"resize_scale_{scale:.2f}")

        if strategy == "raw":
            return resized_img, original_bgr, operations_applied, scale

        gray = self.to_grayscale(resized_img)
        operations_applied.append("grayscale")

        # Auto-deskew attempt
        gray, angle = self.deskew(gray)
        if abs(angle) > 0.5:
            operations_applied.append(f"deskew_{angle:.1f}deg")

        if strategy == "denoise":
            denoised = self.denoise(gray)
            enhanced = self.enhance_contrast(denoised)
            operations_applied.extend(["median_denoise", "clahe_contrast"])
            return enhanced, original_bgr, operations_applied, scale

        elif strategy == "high_contrast":
            enhanced = self.enhance_contrast(gray)
            sharp = self.sharpen(enhanced)
            operations_applied.extend(["clahe_contrast", "sharpen"])
            return sharp, original_bgr, operations_applied, scale

        elif strategy == "binary":
            thresh = self.adaptive_threshold(gray)
            operations_applied.append("adaptive_threshold_binary")
            return thresh, original_bgr, operations_applied, scale

        elif strategy == "upscale":
            upscaled = self.upscale_image(gray, factor=1.5)
            enhanced = self.enhance_contrast(upscaled)
            sharp = self.sharpen(enhanced)
            operations_applied.extend(["upscale_1.5x", "clahe_contrast", "sharpen"])
            return sharp, original_bgr, operations_applied, scale

        elif strategy == "auto":
            # Dynamic strategy selection based on image stats
            std_dev = float(np.std(gray))
            mean_val = float(np.mean(gray))

            if gray.shape[0] < 800 or gray.shape[1] < 800:
                gray = self.upscale_image(gray, factor=1.5)
                operations_applied.append("upscale_1.5x")

            if std_dev < 40.0:  # Low contrast
                enhanced = self.enhance_contrast(gray)
                sharp = self.sharpen(enhanced)
                operations_applied.extend(["clahe_contrast", "sharpen"])
                return sharp, original_bgr, operations_applied, scale
            elif std_dev > 75.0 and (mean_val < 80 or mean_val > 180): # Noisy/uneven
                denoised = self.denoise(gray)
                enhanced = self.enhance_contrast(denoised)
                operations_applied.extend(["median_denoise", "clahe_contrast"])
                return enhanced, original_bgr, operations_applied, scale
            else:
                enhanced = self.enhance_contrast(gray)
                operations_applied.append("clahe_contrast")
                return enhanced, original_bgr, operations_applied, scale

        else:  # 'standard'
            enhanced = self.enhance_contrast(gray)
            operations_applied.append("clahe_contrast")
            return enhanced, original_bgr, operations_applied, scale

