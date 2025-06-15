"""
Image processing module for InvOCR
Handles image loading, processing, and conversion operations
"""

import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Image processing class for handling various image operations
    including preprocessing, enhancement, and format conversion
    """

    def __init__(self):
        """Initialize the image processor"""
        self.supported_formats = [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"]

    def load_image(self, image_path: Union[str, Path]) -> Image.Image:
        """
        Load an image from file

        Args:
            image_path: Path to the image file

        Returns:
            PIL.Image.Image: Loaded image object

        Raises:
            FileNotFoundError: If image file doesn't exist
            IOError: If image cannot be loaded
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        try:
            return Image.open(image_path)
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {str(e)}")
            raise IOError(f"Could not load image: {str(e)}")

    def preprocess_image(
        self,
        image: Image.Image,
        enhance_contrast: bool = True,
        enhance_sharpness: bool = True,
        denoise: bool = True,
        target_dpi: int = 300,
        **kwargs,
    ) -> Image.Image:
        """
        Preprocess image for better OCR results

        Args:
            image: Input PIL Image
            enhance_contrast: Whether to enhance contrast
            enhance_sharpness: Whether to enhance sharpness
            denoise: Whether to apply denoising
            target_dpi: Target DPI for the image

        Returns:
            Preprocessed PIL Image
        """
        # Convert to grayscale if not already
        if image.mode != "L":
            image = image.convert("L")

        # Enhance contrast
        if enhance_contrast:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)

        # Enhance sharpness
        if enhance_sharpness:
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)

        # Denoise
        if denoise:
            image = image.filter(ImageFilter.MedianFilter(size=3))

        # Set DPI if needed
        if target_dpi and hasattr(image, "info"):
            image.info["dpi"] = (target_dpi, target_dpi)

        return image

    def resize_image(
        self,
        image: Image.Image,
        max_size: Tuple[int, int] = None,
        scale_factor: float = None,
    ) -> Image.Image:
        """
        Resize image while maintaining aspect ratio

        Args:
            image: Input PIL Image
            max_size: Maximum (width, height) as tuple
            scale_factor: Scale factor to resize by

        Returns:
            Resized PIL Image
        """
        if max_size and scale_factor:
            raise ValueError("Cannot specify both max_size and scale_factor")

        if max_size:
            # Calculate new size maintaining aspect ratio
            width, height = image.size
            ratio = min(max_size[0] / width, max_size[1] / height)
            new_size = (int(width * ratio), int(height * ratio))
            return image.resize(new_size, Image.Resampling.LANCZOS)
        elif scale_factor:
            new_size = (
                int(image.width * scale_factor),
                int(image.height * scale_factor),
            )
            return image.resize(new_size, Image.Resampling.LANCZOS)

        return image

    def save_image(
        self,
        image: Image.Image,
        output_path: Union[str, Path],
        format: str = None,
        quality: int = 95,
        **kwargs,
    ) -> bool:
        """
        Save image to file

        Args:
            image: PIL Image to save
            output_path: Output file path
            format: Output format (e.g., 'PNG', 'JPEG')
            quality: Image quality (1-100)

        Returns:
            bool: True if save was successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            save_kwargs = {"quality": quality}
            if format:
                save_kwargs["format"] = format

            image.save(output_path, **save_kwargs)
            return True
        except Exception as e:
            logger.error(f"Error saving image to {output_path}: {str(e)}")
            return False

    def convert_to_grayscale(self, image: Image.Image) -> Image.Image:
        """Convert image to grayscale"""
        return image.convert("L")

    def get_image_metadata(self, image: Image.Image) -> Dict[str, Any]:
        """
        Get metadata from image

        Returns:
            Dictionary containing image metadata
        """
        return {
            "format": getattr(image, "format", None),
            "mode": image.mode,
            "size": image.size,
            "info": getattr(image, "info", {}),
        }

    def is_supported_format(self, file_path: Union[str, Path]) -> bool:
        """Check if file format is supported"""
        return Path(file_path).suffix.lower() in self.supported_formats
