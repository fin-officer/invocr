# invocr/formats/pdf.py
"""
PDF processing module
Handles PDF to text/image conversion
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pdfplumber
from pdf2image import convert_from_path

from ..utils.helpers import ensure_directory
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """PDF processing and conversion"""

    def __init__(self):
        self.supported_formats = ['png', 'jpg', 'jpeg']

    def extract_text(self, pdf_path: Union[str, Path]) -> str:
        """Extract text directly from PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""

    def to_images(self, pdf_path: Union[str, Path], output_dir: Union[str, Path],
                  format: str = "png", dpi: int = 300) -> List[str]:
        """Convert PDF pages to images"""
        output_path = ensure_directory(output_dir)
        pdf_name = Path(pdf_path).stem

        try:
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                fmt=format.lower(),
                thread_count=4
            )

            image_paths = []
            for i, image in enumerate(images):
                image_file = output_path / f"{pdf_name}_page_{i + 1}.{format}"
                image.save(image_file, format.upper())
                image_paths.append(str(image_file))
                logger.debug(f"Created image: {image_file}")

            logger.info(f"Converted PDF to {len(image_paths)} images")
            return image_paths

        except Exception as e:
            logger.error(f"PDF to images conversion failed: {e}")
            return []

    def get_page_count(self, pdf_path: Union[str, Path]) -> int:
        """Get number of pages in PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0

    def extract_tables(self, pdf_path: Union[str, Path]) -> List[List]:
        """Extract tables from PDF"""
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    tables.extend(page_tables)
            return tables
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            return []


# ---

# invocr/formats/image.py
"""
Image processing module
Handles image operations and preprocessing
"""

from pathlib import Path
from typing import Tuple, Union

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """Image processing and enhancement"""

    def __init__(self):
        self.supported_formats = ['png', 'jpg', 'jpeg', 'tiff', 'bmp']

    def preprocess_for_ocr(self, image_path: Union[str, Path]) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Load image
            if not isinstance(image_path, (str, Path)):
                raise ValueError("image_path must be a string or Path object")
                
            # Read the image
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Could not read image from {image_path}")
                
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding to get binary image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Apply some denoising
            denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
            
            # Apply adaptive thresholding
            adaptive = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            return adaptive
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise

    def from_html(self, html_input: Union[str, Path]) -> Dict[str, Any]:
        """Extract data from HTML (basic implementation)"""
        # This would require HTML parsing - simplified version
        return {"extracted_from": "html", "content": "basic_extraction"}

    def _prepare_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare template context with additional data"""
        context = data.copy()

        # Add utility functions and formatting
        context.update({
            "current_date": "2025-06-15",
            "currency": "PLN",
            "company_logo": "",
            "formatted_totals": self._format_currency_values(data.get("totals", {}))
        })

        return context

    def _format_currency_values(self, totals: Dict) -> Dict:
        """Format currency values for display"""
        return {
            "subtotal": f"{totals.get('subtotal', 0):.2f}",
            "tax_amount": f"{totals.get('tax_amount', 0):.2f}",
            "total": f"{totals.get('total', 0):.2f}"
        }

    def _get_modern_template(self) -> str:
        """Modern responsive template"""
        return """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faktura {{ document_number }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
               line-height: 1.6; color: #333; background: #f8f9fa; }
        .container { max-width: 900px; margin: 20px auto; background: white; 
                     padding: 40px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 3px solid #007bff; 
                  padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #007bff; font-size: 2.5em; font-weight: 300; }
        .invoice-info { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }
        .info-card { background: #f8f9fa; padding: 20px; border-radius: 8px; }
        .info-card h3 { color: #007bff; margin-bottom: 15px; }
        .parties { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }
        .party { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 color: white; padding: 25px; border-radius: 10px; }
        .party h3 { margin-bottom: 15px; font-weight: 300; }
        .items { margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #e9ecef; }
        th { background: #007bff; color: white; font-weight: 600; }
        tbody tr:hover { background: #f8f9fa; }
        .number { text-align: right; }
        .totals { float: right; background: #f8f9fa; padding: 25px; 
                  border-radius: 10px; min-width: 300px; margin-bottom: 30px; }
        .total-row { display: flex; justify-content: space-between; padding: 8px 0; }
        .total-final { font-weight: bold; font-size: 1.2em; color: #007bff; 
                       border-top: 2px solid #007bff; margin-top: 10px; padding-top: 10px; }
        .footer { clear: both; border-top: 1px solid #e9ecef; padding-top: 20px; color: #666; }
        @media print { body { background: white; } .container { box-shadow: none; margin: 0; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>FAKTURA</h1>
            <p>Nr: {{ document_number }}</p>
        </div>

        <div class="invoice-info">
            <div class="info-card">
                <h3>Informacje o dokumencie</h3>
                <p><strong>Data wystawienia:</strong> {{ document_date }}</p>
                <p><strong>Termin płatności:</strong> {{ due_date }}</p>
                <p><strong>Sposób płatności:</strong> {{ payment_method }}</p>
            </div>
            <div class="info-card">
                <h3>Płatność</h3>
                <p><strong>Nr konta:</strong> {{ bank_account }}</p>
                <p><strong>Waluta:</strong> {{ currency }}</p>
            </div>
        </div>
    </div>
</body>
</html>"""