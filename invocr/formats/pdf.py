# invocr/formats/pdf.py
"""
PDF processing module
Handles PDF to text/image conversion
"""

import tempfile
from pathlib import Path
from typing import List, Optional, Union

import pdfplumber
from pdf2image import convert_from_path

from ..utils.logger import get_logger
from ..utils.helpers import ensure_directory

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

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
from typing import Tuple, Union

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
            if isinstance(image_path, (str, Path)):
                image = cv2.imread(str(image_path))
            else:
                html_doc = weasyprint.HTML(string=html_input)

            css = weasyprint.CSS(string=css_string)
            html_doc.write_pdf(output_path, stylesheets=[css])

            logger.info(f"PDF generated: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"HTML to PDF conversion failed: {e}")
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

        <div class="parties">
            <div class="party">
                <h3>📤 Sprzedawca</h3>
                <p><strong>{{ seller.name }}</strong></p>
                <p>{{ seller.address }}</p>
                <p>NIP: {{ seller.tax_id }}</p>
                <p>Tel: {{ seller.phone }}</p>
                <p>Email: {{ seller.email }}</p>
            </div>
            <div class="party">
                <h3>📥 Nabywca</h3>
                <p><strong>{{ buyer.name }}</strong></p>
                <p>{{ buyer.address }}</p>
                <p>NIP: {{ buyer.tax_id }}</p>
                <p>Tel: {{ buyer.phone }}</p>
                <p>Email: {{ buyer.email }}</p>
            </div>
        </div>

        <div class="items">
            <table>
                <thead>
                    <tr>
                        <th>Lp.</th>
                        <th>Opis</th>
                        <th>Ilość</th>
                        <th>Cena jedn.</th>
                        <th>Wartość</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in items %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ item.description }}</td>
                        <td class="number">{{ item.quantity }}</td>
                        <td class="number">{{ "%.2f"|format(item.unit_price) }} {{ currency }}</td>
                        <td class="number">{{ "%.2f"|format(item.total_price) }} {{ currency }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="totals">
            <div class="total-row">
                <span>Suma netto:</span>
                <span>{{ formatted_totals.subtotal }} {{ currency }}</span>
            </div>
            <div class="total-row">
                <span>VAT ({{ totals.tax_rate }}%):</span>
                <span>{{ formatted_totals.tax_amount }} {{ currency }}</span>
            </div>
            <div class="total-row total-final">
                <span>RAZEM:</span>
                <span>{{ formatted_totals.total }} {{ currency }}</span>
            </div>
        </div>

        <div class="footer">
            <p><strong>Uwagi:</strong> {{ notes }}</p>
            <p><em>Dokument wygenerowany przez InvOCR v1.0.0</em></p>
        </div>
    </div>
</body>
</html>"""

    def _get_classic_template(self) -> str:
        """Classic business template"""
        return """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>Faktura {{ document_number }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; color: #000; }
        .header { text-align: center; border-bottom: 2px solid #000; margin-bottom: 30px; }
        .header h1 { font-size: 24px; margin: 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #000; padding: 8px; text-align: left; }
        th { background-color: #f0f0f0; font-weight: bold; }
        .right { text-align: right; }
        .total { font-weight: bold; background-color: #f0f0f0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>FAKTURA {{ document_number }}</h1>
        <p>Data: {{ document_date }} | Termin: {{ due_date }}</p>
    </div>

    <table>
        <tr><th>Sprzedawca</th><th>Nabywca</th></tr>
        <tr>
            <td>{{ seller.name }}<br>{{ seller.address }}<br>NIP: {{ seller.tax_id }}</td>
            <td>{{ buyer.name }}<br>{{ buyer.address }}<br>NIP: {{ buyer.tax_id }}</td>
        </tr>
    </table>

    <table>
        <tr><th>Lp.</th><th>Opis</th><th>Ilość</th><th>Cena</th><th>Wartość</th></tr>
        {% for item in items %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ item.description }}</td>
            <td class="right">{{ item.quantity }}</td>
            <td class="right">{{ "%.2f"|format(item.unit_price) }}</td>
            <td class="right">{{ "%.2f"|format(item.total_price) }}</td>
        </tr>
        {% endfor %}
        <tr class="total">
            <td colspan="4">RAZEM DO ZAPŁATY:</td>
            <td class="right">{{ "%.2f"|format(totals.total) }} {{ currency }}</td>
        </tr>
    </table>
</body>
</html>"""

    def _get_minimal_template(self) -> str:
        """Minimal clean template"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ document_number }}</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; border-bottom: 1px solid #eee; }
        th { background: #f5f5f5; }
        .total { font-weight: bold; font-size: 1.2em; }
    </style>
</head>
<body>
    <h1>Faktura {{ document_number }}</h1>

    <div class="grid">
        <div><strong>Sprzedawca:</strong><br>{{ seller.name }}</div>
        <div><strong>Nabywca:</strong><br>{{ buyer.name }}</div>
    </div>

    <table>
        <tr><th>Opis</th><th>Ilość</th><th>Cena</th><th>Wartość</th></tr>
        {% for item in items %}
        <tr>
            <td>{{ item.description }}</td>
            <td>{{ item.quantity }}</td>
            <td>{{ "%.2f"|format(item.unit_price) }}</td>
            <td>{{ "%.2f"|format(item.total_price) }}</td>
        </tr>
        {% endfor %}
    </table>

    <p class="total">Razem: {{ "%.2f"|format(totals.total) }} {{ currency }}</p>
</body>
</html>"""
        image = image_path

    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

        # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply preprocessing pipeline
    processed = self._apply_preprocessing_pipeline(gray)

    return processed

except Exception as e:
logger.error(f"Image preprocessing failed: {e}")
raise


def _apply_preprocessing_pipeline(self, image: np.ndarray) -> np.ndarray:
    """Apply comprehensive preprocessing pipeline"""
    # 1. Noise reduction
    denoised = cv2.medianBlur(image, 3)

    # 2. Contrast enhancement using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    # 3. Adaptive thresholding
    binary = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # 4. Morphological operations
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # 5. Deskewing if needed
    deskewed = self._deskew_image(cleaned)

    return deskewed


def _deskew_image(self, image: np.ndarray) -> np.ndarray:
    """Detect and correct skew in image"""
    try:
        # Find contours
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Find the largest contour (likely the document)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)

            # Get minimum area rectangle
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[2]

            # Correct angle
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90

            # Apply rotation if significant skew detected
            if abs(angle) > 1:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(image, rotation_matrix, (w, h),
                                         flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated

        return image

    except Exception as e:
        logger.warning(f"Deskewing failed: {e}")
        return image


def enhance_image_quality(self, image_path: Union[str, Path],
                          output_path: Optional[Union[str, Path]] = None) -> str:
    """Enhance image quality using PIL"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)

            # Apply unsharp mask
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

            # Resize if too small
            width, height = img.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Save enhanced image
            if output_path is None:
                output_path = tempfile.mktemp(suffix='.png')

            img.save(output_path, 'PNG', quality=95, optimize=True)
            return str(output_path)

    except Exception as e:
        logger.error(f"Image enhancement failed: {e}")
        return str(image_path)


def get_image_info(self, image_path: Union[str, Path]) -> dict:
    """Get image information"""
    try:
        with Image.open(image_path) as img:
            return {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height
            }
    except Exception as e:
        logger.error(f"Could not get image info: {e}")
        return {}


# ---

# invocr/formats/json_handler.py
"""
JSON format handler
Handles JSON operations and validation
"""

import json
from pathlib import Path
from typing import Any, Dict, Union
from datetime import datetime

from ..utils.logger import get_logger
from ..utils.helpers import safe_json_loads, safe_json_dumps

logger = get_logger(__name__)


class JSONHandler:
    """JSON format operations"""

    def __init__(self):
        self.schema_version = "1.0"

    def load(self, json_input: Union[str, Path, Dict]) -> Dict[str, Any]:
        """Load JSON from file or string"""
        if isinstance(json_input, dict):
            return json_input

        if isinstance(json_input, Path) or (isinstance(json_input, str) and Path(json_input).exists()):
            with open(json_input, 'r', encoding='utf-8') as f:
                return json.load(f)

        return safe_json_loads(json_input, {})

    def save(self, data: Dict[str, Any], output_path: Union[str, Path]) -> bool:
        """Save data to JSON file"""
        try:
            # Add metadata
            data_with_meta = self._add_metadata(data)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_with_meta, f, ensure_ascii=False, indent=2)

            logger.info(f"JSON saved to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"JSON save failed: {e}")
            return False

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate JSON structure"""
        required_fields = ["document_number", "items", "totals"]

        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False

        return True

    def _add_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata to JSON"""
        if "_metadata" not in data:
            data["_metadata"] = {}

        data["_metadata"].update({
            "schema_version": self.schema_version,
            "generated_at": datetime.now().isoformat(),
            "generator": "InvOCR v1.0.0"
        })

        return data


# ---

# invocr/formats/html_handler.py
"""
HTML format handler
Generates responsive HTML invoices
"""

import tempfile
from pathlib import Path
from typing import Dict, Any, Union, Optional
import weasyprint
from jinja2 import Template

from ..utils.logger import get_logger

logger = get_logger(__name__)


class HTMLHandler:
    """HTML generation and PDF conversion"""

    def __init__(self):
        self.templates = {
            "modern": self._get_modern_template(),
            "classic": self._get_classic_template(),
            "minimal": self._get_minimal_template()
        }

    def to_html(self, data: Dict[str, Any], template: str = "modern") -> str:
        """Convert data to HTML"""
        try:
            template_content = self.templates.get(template, self.templates["modern"])
            jinja_template = Template(template_content)

            # Prepare context
            context = self._prepare_context(data)

            html_content = jinja_template.render(**context)
            return html_content

        except Exception as e:
            logger.error(f"HTML generation failed: {e}")
            return ""

    def to_pdf(self, html_input: Union[str, Path], output_path: Union[str, Path],
               options: Optional[Dict] = None) -> str:
        """Convert HTML to PDF"""
        try:
            default_options = {
                "page_size": "A4",
                "margin": "20mm",
                "encoding": "utf-8"
            }

            if options:
                default_options.update(options)

            # Create CSS for page settings
            css_string = f"""
                @page {{
                    size: {default_options['page_size']};
                    margin: {default_options['margin']};
                }}
            """

            if isinstance(html_input, Path) or Path(html_input).exists():
                html_doc = weasyprint.HTML(filename=str(html_input))
            else:
                html_doc = weasyprint.HTML(string=html_input)

            # Create temporary file for CSS
            with tempfile.NamedTemporaryFile(delete=False) as css_file:
                css_file.write(css_string.encode('utf-8'))
                css_file.close()

                # Create temporary file for HTML
                with tempfile.NamedTemporaryFile(delete=False) as html_file:
                    html_file.write(html_doc.encode('utf-8'))
                    html_file.close()

                    # Convert HTML to PDF
                    weasyprint.HTML(string=html_doc).write_pdf(
                        output_path,
                        stylesheets=[weasyprint.CSS(css_file.name)],
                        **default_options
                    )

                    return output_path

        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return ""