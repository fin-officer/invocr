"""
OCR Engine for invoice processing using Tesseract and EasyOCR
Supports multiple languages and document types
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import easyocr
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

from ..utils.config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OCREngine:
    """Multi-engine OCR processor with preprocessing and optimization"""

    def __init__(self, languages: List[str] = None):
        self.languages = languages or ["en", "pl", "de", "fr", "es", "it"]
        self.tesseract_langs = "+".join(self._map_languages(self.languages))
        self.easyocr = easyocr.Reader(self.languages, gpu=False)
        logger.info(f"OCR initialized with languages: {self.languages}")

    def extract_text(
        self, image_path: Union[str, Path], engine: str = "auto"
    ) -> Dict[str, any]:
        """
        Extract text from image using specified OCR engine

        Args:
            image_path: Path to image file
            engine: OCR engine ('tesseract', 'easyocr', 'auto')

        Returns:
            Dict with extracted text and metadata
        """
        try:
            image = self._load_and_preprocess(image_path)

            if engine == "auto":
                # Try both engines and use best result
                results = {}
                for eng in ["tesseract", "easyocr"]:
                    try:
                        results[eng] = self._extract_with_engine(image, eng)
                    except Exception as e:
                        logger.warning(f"Engine {eng} failed: {e}")
                        results[eng] = {"text": "", "confidence": 0.0}

                # Select best result based on confidence
                best_engine = max(
                    results.keys(), key=lambda k: results[k]["confidence"]
                )
                result = results[best_engine]
                result["engine_used"] = best_engine

            else:
                result = self._extract_with_engine(image, engine)
                result["engine_used"] = engine

            result["languages"] = self.languages
            return result

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}

    def _load_and_preprocess(self, image_path: Union[str, Path]) -> np.ndarray:
        """Load and preprocess image for better OCR accuracy"""
        # Load image
        if isinstance(image_path, (str, Path)):
            image = cv2.imread(str(image_path))
        else:
            image = image_path

        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply preprocessing techniques
        processed = self._apply_preprocessing(gray)

        return processed

    def _apply_preprocessing(self, image: np.ndarray) -> np.ndarray:
        """Apply image preprocessing for better OCR results"""
        # Noise reduction
        denoised = cv2.medianBlur(image, 3)

        # Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return cleaned

    def _extract_with_engine(self, image: np.ndarray, engine: str) -> Dict[str, any]:
        """Extract text using specific OCR engine"""
        if engine == "tesseract":
            return self._extract_tesseract(image)
        elif engine == "easyocr":
            return self._extract_easyocr(image)
        else:
            raise ValueError(f"Unknown OCR engine: {engine}")

    def _extract_tesseract(self, image: np.ndarray) -> Dict[str, any]:
        """Extract text using Tesseract OCR"""
        config = r"--oem 3 --psm 6"

        # Extract text with confidence
        data = pytesseract.image_to_data(
            image,
            lang=self.tesseract_langs,
            config=config,
            output_type=pytesseract.Output.DICT,
        )

        # Filter out low confidence detections
        text_parts = []
        confidences = []

        for i, conf in enumerate(data["conf"]):
            if int(conf) > 30:  # Minimum confidence threshold
                text = data["text"][i].strip()
                if text:
                    text_parts.append(text)
                    confidences.append(int(conf))

        full_text = " ".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "text": full_text,
            "confidence": avg_confidence / 100.0,  # Normalize to 0-1
            "word_count": len(text_parts),
            "raw_data": data,
        }

    def _extract_easyocr(self, image: np.ndarray) -> Dict[str, any]:
        """Extract text using EasyOCR"""
        results = self.easyocr.readtext(image)

        text_parts = []
        confidences = []

        for bbox, text, conf in results:
            if conf > 0.3:  # Minimum confidence threshold
                text_parts.append(text)
                confidences.append(conf)

        full_text = " ".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "text": full_text,
            "confidence": avg_confidence,
            "word_count": len(text_parts),
            "raw_data": results,
        }

    def _map_languages(self, languages: List[str]) -> List[str]:
        """Map language codes to Tesseract language codes"""
        lang_map = {
            "en": "eng",
            "pl": "pol",
            "de": "deu",
            "fr": "fra",
            "es": "spa",
            "it": "ita",
            "pt": "por",
            "nl": "nld",
            "ru": "rus",
            "cs": "ces",
            "sk": "slk",
            "hu": "hun",
        }
        return [lang_map.get(lang, lang) for lang in languages]

    def detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns"""
        # Polish specific characters
        if any(char in text for char in "ąćęłńóśźż"):
            return "pl"

        # German specific characters
        if any(char in text for char in "äöüß"):
            return "de"

        # French specific characters
        if any(char in text for char in "àâäéèêëïîôùûüÿç"):
            return "fr"

        # Spanish specific characters
        if any(char in text for char in "ñáéíóúü"):
            return "es"

        # Default to English
        return "en"

    def enhance_image_quality(self, image_path: Union[str, Path]) -> str:
        """Enhance image quality before OCR processing"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            # Load with PIL for enhancement
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Enhance sharpness
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.5)

                # Enhance contrast
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)

                # Apply unsharp mask
                img = img.filter(
                    ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3)
                )

                # Resize if too small
                width, height = img.size
                if width < 1000 or height < 1000:
                    scale_factor = max(1000 / width, 1000 / height)
                    new_size = (int(width * scale_factor), int(height * scale_factor))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Save enhanced image
                img.save(tmp.name, "PNG", quality=95, optimize=True)

            return tmp.name

    def extract_regions(
        self, image_path: Union[str, Path], regions: List[Tuple[int, int, int, int]]
    ) -> List[Dict]:
        """Extract text from specific regions of the image"""
        results = []
        image = cv2.imread(str(image_path))

        for i, (x, y, w, h) in enumerate(regions):
            # Extract region
            region = image[y : y + h, x : x + w]

            # Process region
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                cv2.imwrite(tmp.name, region)

                # Extract text from region
                result = self.extract_text(tmp.name)
                result["region_id"] = i
                result["coordinates"] = (x, y, w, h)
                results.append(result)

                # Cleanup
                os.unlink(tmp.name)

        return results


def create_ocr_engine(languages: List[str] = None) -> OCREngine:
    """Factory function to create OCR engine instance"""
    return OCREngine(languages=languages)
