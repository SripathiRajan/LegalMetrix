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

        else:  # 'standard'
            enhanced = self.enhance_contrast(gray)
            operations_applied.append("clahe_contrast")
            return enhanced, original_bgr, operations_applied, scale
