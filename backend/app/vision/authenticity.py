import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np

from app.models.extracted_product import AuthenticityResult, AuthenticityVerdict
from app.vision.bbox_utils import BBoxUtils

logger = logging.getLogger(__name__)

# Default reference brand storage path
DEFAULT_REFERENCE_DIR = Path(__file__).parent / "reference_brands"


class AuthenticityChecker:
    """
    Brand Packaging Authenticity and Anti-Counterfeiting Verification Engine:
      - Uses DINOv2 (facebook/dinov2-base) self-supervised vision transformer embeddings
      - Lazy-loads PyTorch + Transformers with graceful fallback pattern
      - Computes full-image and cropped logo embeddings, dominant color palette (k-means k=5),
        and relative height ratio
      - Compares sample packaging against verified reference brand embeddings
    """

    def __init__(
        self,
        model_name: str = "facebook/dinov2-base",
        reference_dir: Optional[Union[str, Path]] = None,
        default_threshold: float = 0.80
    ):
        self.model_name = model_name
        self.reference_dir = Path(reference_dir) if reference_dir else DEFAULT_REFERENCE_DIR
        self.reference_dir.mkdir(parents=True, exist_ok=True)
        self.default_threshold = default_threshold

        self.model = None
        self.processor = None
        self.device = None
        self._initialize_engine()

    def _initialize_engine(self):
        """
        Lazy-loads DINOv2 vision transformer using identical graceful fallback pattern as PaddleOCREngine.
        """
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModel

            logger.info(f"Initializing DINOv2 authenticity engine ({self.model_name})...")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.processor = AutoImageProcessor.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
            self.model.eval()
            logger.info("DINOv2 authenticity engine initialized successfully.")
        except Exception as e:
            logger.warning(f"DINOv2 model not initialized ({str(e)}). Running in fallback/mock mode.")
            self.model = None
            self.processor = None
            self.device = "cpu"

    @staticmethod
    def _to_numpy_image(image: Any) -> np.ndarray:
        """Converts input image (bytes, filepath, PIL, or numpy) to numpy BGR/RGB array."""
        if isinstance(image, np.ndarray):
            return image

        if isinstance(image, (bytes, bytearray)):
            import cv2
            nparr = np.frombuffer(image, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes")
            return img

        if isinstance(image, (str, Path)):
            import cv2
            img = cv2.imread(str(image))
            if img is None:
                raise ValueError(f"Could not load image from path: {image}")
            return img

        # PIL Image
        try:
            from PIL import Image
            if isinstance(image, Image.Image):
                return np.array(image.convert("RGB"))
        except ImportError:
            pass

        raise ValueError(f"Unsupported image type: {type(image)}")

    @staticmethod
    def extract_dominant_palette(image: np.ndarray, k: int = 5) -> List[List[int]]:
        """
        Extracts top k dominant RGB colors using OpenCV cv2.kmeans.
        """
        try:
            import cv2
            if image is None or image.size == 0:
                return [[255, 255, 255]] * k

            small_img = cv2.resize(image, (64, 64), interpolation=cv2.INTER_AREA)

            if len(small_img.shape) == 2:
                small_img = cv2.cvtColor(small_img, cv2.COLOR_GRAY2RGB)
            elif small_img.shape[2] == 4:
                small_img = cv2.cvtColor(small_img, cv2.COLOR_BGRA2RGB)
            elif small_img.shape[2] == 3:
                small_img = cv2.cvtColor(small_img, cv2.COLOR_BGR2RGB)

            pixels = small_img.reshape(-1, 3).astype(np.float32)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.2)
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            counts = np.bincount(labels.flatten())
            sorted_indices = np.argsort(-counts)

            dominant_rgb = [
                [int(np.clip(round(centers[idx][0]), 0, 255)),
                 int(np.clip(round(centers[idx][1]), 0, 255)),
                 int(np.clip(round(centers[idx][2]), 0, 255))]
                for idx in sorted_indices
            ]
            return dominant_rgb
        except Exception as e:
            logger.warning(f"Error extracting color palette: {str(e)}")
            return [[255, 255, 255], [0, 0, 0], [128, 128, 128], [200, 200, 200], [50, 50, 50]]

    @staticmethod
    def compute_color_similarity(
        palette1: List[List[int]],
        palette2: List[List[int]]
    ) -> float:
        """
        Computes normalized color palette similarity in [0.0, 1.0] by evaluating
        closest RGB Euclidean distance between color centroids.
        """
        if not palette1 or not palette2:
            return 0.0

        p1 = np.array(palette1, dtype=np.float32)
        p2 = np.array(palette2, dtype=np.float32)

        max_dist = np.sqrt(255.0**2 * 3.0)  # ~441.67

        # Average distance from palette1 to nearest in palette2
        dists_1_to_2 = [np.min(np.linalg.norm(p2 - color, axis=1)) for color in p1]
        dists_2_to_1 = [np.min(np.linalg.norm(p1 - color, axis=1)) for color in p2]

        avg_dist = (np.mean(dists_1_to_2) + np.mean(dists_2_to_1)) / 2.0
        similarity = max(0.0, min(1.0, 1.0 - (avg_dist / max_dist)))
        return round(float(similarity), 4)

    def _extract_dinov2_features(self, image_np: np.ndarray) -> np.ndarray:
        """
        Passes image through DINOv2 model to extract normalized 768-d [CLS] embedding.
        """
        if self.model is None or self.processor is None:
            # Deterministic fallback embedding based on image shape/summary for testing
            h, w = image_np.shape[:2]
            rng = np.random.RandomState(abs(h * 31 + w * 17) % 10000)
            raw_vec = rng.randn(768).astype(np.float32)
            norm = np.linalg.norm(raw_vec)
            return raw_vec / max(1e-8, norm)

        try:
            import torch
            from PIL import Image

            if len(image_np.shape) == 2:
                pil_img = Image.fromarray(image_np).convert("RGB")
            else:
                import cv2
                rgb_img = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)

            inputs = self.processor(images=pil_img, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                # DINOv2 last_hidden_state: shape (batch_size, sequence_length, hidden_size)
                # Token 0 is the [CLS] representation
                cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy()

            norm = np.linalg.norm(cls_embedding)
            if norm > 0:
                cls_embedding = cls_embedding / norm

            return cls_embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"Error extracting DINOv2 features: {str(e)}")
            raw_vec = np.zeros(768, dtype=np.float32)
            return raw_vec

    def compute_embedding(
        self,
        image: Any,
        logo_bbox: Optional[Union[List[List[float]], List[float]]] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray], List[List[int]], Optional[float]]:
        """
        Computes:
          - Full-image normalized visual embedding
          - Optional cropped logo embedding (if logo_bbox provided)
          - Dominant color palette (k-means k=5)
          - Font/logo height ratio relative to image height
        """
        img_np = self._to_numpy_image(image)
        img_h, img_w = img_np.shape[:2]

        # 1. Full Image Embedding
        full_embedding = self._extract_dinov2_features(img_np)

        # 2. Dominant Palette
        dominant_palette = self.extract_dominant_palette(img_np, k=5)

        # 3. Logo Embedding & Height Ratio
        logo_embedding = None
        font_height_ratio = None

        if logo_bbox:
            xyxy = BBoxUtils.to_xyxy(logo_bbox)
            xmin, ymin, xmax, ymax = [int(v) for v in xyxy]
            xmin = max(0, min(img_w - 1, xmin))
            ymin = max(0, min(img_h - 1, ymin))
            xmax = max(xmin + 1, min(img_w, xmax))
            ymax = max(ymin + 1, min(img_h, ymax))

            cropped_logo = img_np[ymin:ymax, xmin:xmax]
            if cropped_logo.size > 0:
                logo_embedding = self._extract_dinov2_features(cropped_logo)

            _, box_h = BBoxUtils.get_dimensions(logo_bbox)
            font_height_ratio = round(box_h / float(img_h), 4) if img_h > 0 else 0.0

        return full_embedding, logo_embedding, dominant_palette, font_height_ratio

    def save_reference_brand(
        self,
        brand_id: str,
        image: Any,
        logo_bbox: Optional[Union[List[List[float]], List[float]]] = None,
        brand_name: Optional[str] = None
    ) -> Path:
        """
        Computes and saves verified reference brand packaging embedding to reference storage.
        """
        clean_brand_id = brand_id.strip().lower().replace(" ", "_")
        full_emb, logo_emb, palette, ratio = self.compute_embedding(image, logo_bbox=logo_bbox)

        ref_data = {
            "brand_id": clean_brand_id,
            "brand_name": brand_name or brand_id,
            "embedding": full_emb,
            "logo_embedding": logo_emb,
            "palette": palette,
            "font_height_ratio": ratio
        }

        target_path = self.reference_dir / f"{clean_brand_id}.npy"
        np.save(target_path, ref_data, allow_pickle=True)
        logger.info(f"Registered reference brand '{clean_brand_id}' at {target_path}")
        return target_path

    def load_reference_brand(self, brand_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads reference brand embeddings and metadata from storage.
        """
        clean_brand_id = brand_id.strip().lower().replace(" ", "_")
        target_path = self.reference_dir / f"{clean_brand_id}.npy"

        if not target_path.exists():
            # Check for alternative extensions
            npz_path = self.reference_dir / f"{clean_brand_id}.npz"
            if npz_path.exists():
                data = np.load(npz_path, allow_pickle=True)
                return dict(data)
            return None

        try:
            loaded = np.load(target_path, allow_pickle=True)
            if loaded.shape == ():
                return loaded.item()
            elif isinstance(loaded, np.ndarray):
                # Raw embedding vector
                return {
                    "brand_id": clean_brand_id,
                    "embedding": loaded,
                    "palette": [],
                    "logo_embedding": None,
                    "font_height_ratio": None
                }
            return None
        except Exception as e:
            logger.error(f"Error loading reference brand '{brand_id}': {str(e)}")
            return None

    def compare_to_reference(
        self,
        image: Any,
        brand_id: str,
        logo_bbox: Optional[Union[List[List[float]], List[float]]] = None,
        threshold: Optional[float] = None
    ) -> AuthenticityResult:
        """
        Evaluates sample product packaging against verified reference brand embedding.
        """
        thresh = threshold if threshold is not None else self.default_threshold
        ref_data = self.load_reference_brand(brand_id)

        if ref_data is None:
            return AuthenticityResult(
                similarity_score=0.0,
                verdict=AuthenticityVerdict.NO_REFERENCE_AVAILABLE,
                threshold_used=thresh,
                color_similarity=None,
                notes=f"No verified reference brand embedding found for '{brand_id}' in catalog.",
                brand_name=brand_id
            )

        # Compute sample packaging embedding
        full_emb, logo_emb, palette, ratio = self.compute_embedding(image, logo_bbox=logo_bbox)

        ref_emb = ref_data.get("embedding")
        if ref_emb is None:
            return AuthenticityResult(
                similarity_score=0.0,
                verdict=AuthenticityVerdict.NO_REFERENCE_AVAILABLE,
                threshold_used=thresh,
                color_similarity=None,
                notes="Reference data contains corrupted embedding.",
                brand_name=brand_id
            )

        # 1. Cosine similarity of full visual features
        norm_sample = np.linalg.norm(full_emb)
        norm_ref = np.linalg.norm(ref_emb)
        if norm_sample > 0 and norm_ref > 0:
            cosine_sim = float(np.dot(full_emb, ref_emb) / (norm_sample * norm_ref))
            cosine_sim = max(0.0, min(1.0, cosine_sim))
        else:
            cosine_sim = 0.0

        # 2. Color similarity
        ref_palette = ref_data.get("palette", [])
        color_sim = self.compute_color_similarity(palette, ref_palette) if ref_palette else None

        # 3. Overall similarity & verdict
        effective_score = round(cosine_sim, 4)

        if effective_score >= thresh:
            verdict = AuthenticityVerdict.GENUINE_LIKELY
            notes = f"Visual appearance aligns with reference brand catalog (similarity: {effective_score:.2%})."
        else:
            verdict = AuthenticityVerdict.SUSPICIOUS
            notes = (
                f"Visual appearance diverges from reference brand catalog "
                f"(similarity {effective_score:.2%} < threshold {thresh:.2%}). "
                f"Possible counterfeit or unauthorized packaging variation."
            )

        return AuthenticityResult(
            similarity_score=effective_score,
            verdict=verdict,
            threshold_used=thresh,
            color_similarity=color_sim,
            notes=notes,
            brand_name=ref_data.get("brand_name", brand_id),
            dominant_palette=palette,
            font_height_ratio=ratio
        )
