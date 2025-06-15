# invocr/formats/pdf.py
"""
PDF processing module
Handles PDF to text/image conversion and structured data extraction
"""

import json
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pdfplumber
from dateutil.parser import parse as parse_date
from pdf2image import convert_from_path

from ..utils.helpers import ensure_directory
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class InvoiceItem:
    """Represents an invoice line item"""

    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0
    currency: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class InvoiceTotals:
    """Represents invoice totals"""

    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    currency: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class PDFProcessor:
    """PDF processing and structured data extraction"""

    def __init__(self):
        self.supported_formats = ["png", "jpg", "jpeg"]
        self.patterns = {
            "document_number": [
                r"(?i)(?:invoice|document|receipt)[\s:]*([A-Z0-9-]+)",
                r"(?i)No\.?[\s:]*([A-Z0-9-]+)",
                r"(?i)Invoice\s*#?:?\s*([A-Z0-9-]+)",
            ],
            "date": [
                r"(?i)(?:date|issue date|invoice date|date issued)[\s:]*([\d/.-]+)",
                r"(?i)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"(?i)(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            ],
            "currency": [
                r"([A-Z]{3})",  # Currency code like USD, EUR, etc.
                r"([$€£¥])\s*\d",  # Currency symbol followed by number
            ],
            "amount": [
                r"(?i)total[\s:]*([$€£¥]?[\d,.]+)",
                r"(?i)amount[\s:]*([$€£¥]?[\d,.]+)",
                r"\b([$€£¥]?[\d,]+(?:\.[\d]{2})?)\b",
            ],
        }

    def extract_text(self, pdf_path: Union[str, Path]) -> str:
        """
        Extract text directly from PDF with improved layout preservation

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text with preserved layout
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    # Extract text with layout preservation
                    page_text = page.extract_text(
                        x_tolerance=3,
                        y_tolerance=3,
                        keep_blank_chars=False,
                        use_text_flow=True,
                        extra_attrs=["fontname", "size"],
                    )
                    if page_text:
                        text += page_text + "\n\n"
                return text.strip()
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""

    def to_images(
        self,
        pdf_path: Union[str, Path],
        output_dir: Union[str, Path],
        format: str = "png",
        dpi: int = 300,
    ) -> List[str]:
        """Convert PDF pages to images"""
        output_path = ensure_directory(output_dir)
        pdf_name = Path(pdf_path).stem

        try:
            images = convert_from_path(
                pdf_path, dpi=dpi, fmt=format.lower(), thread_count=4
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

    def extract_structured_data(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract structured data from an invoice PDF

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with structured invoice data
        """
        try:
            # Extract text from PDF
            text = self.extract_text(pdf_path)
            if not text:
                logger.error("No text extracted from PDF")
                return {}

            # Initialize result dictionary
            result = {
                "document_number": self._extract_document_number(text),
                "document_date": self._extract_date(text, "document"),
                "due_date": self._extract_date(text, "due"),
                "seller": self._extract_party(text, "seller"),
                "buyer": self._extract_party(text, "buyer"),
                "items": self._extract_items(text),
                "totals": self._extract_totals(text),
                "payment_terms": self._extract_payment_terms(text),
                "notes": self._extract_notes(text),
                "_metadata": {
                    "source_type": "pdf_text",
                    "extraction_method": "enhanced",
                    "document_type": "invoice",
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                },
            }

            return result

        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {}

    def _extract_document_number(self, text: str) -> str:
        """Extract document number from text"""
        for pattern in self.patterns["document_number"]:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_date(self, text: str, date_type: str = "document") -> str:
        """Extract date from text"""
        date_patterns = self.patterns["date"]
        if date_type == "due":
            # Try to find due date specific patterns first
            due_patterns = [
                r"(?i)due date[\s:]*([\d/.-]+)",
                r"(?i)payment due[\s:]*([\d/.-]+)",
                r"(?i)pay by[\s:]*([\d/.-]+)",
            ] + date_patterns
            patterns = due_patterns
        else:
            patterns = date_patterns

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1).strip()
                    # Try to parse the date
                    date_obj = parse_date(date_str, fuzzy=True)
                    return date_obj.strftime("%Y-%m-%d")
                except (ValueError, AttributeError):
                    continue
        return ""

    def _extract_party(self, text: str, party_type: str) -> Dict[str, str]:
        """
        Extract party information (seller/buyer) using regex patterns

        Args:
            text: Full text of the invoice
            party_type: Either 'seller' or 'buyer'

        Returns:
            Dictionary with party information
        """
        party = {"name": "", "address": "", "email": "", "tax_id": ""}

        # Common patterns for seller/buyer sections
        patterns = {
            "name": [
                rf"(?i){party_type}[\s:]*([^\n\r]+)",
                rf"(?i)from:?\s*([^\n\r]+)",
                rf"(?i)to:?\s*([^\n\r]+)",
            ],
            "address": [
                rf"(?i){party_type}[\s\S]*?\b(?:address|location)[\s:]*([^\n\r]+(?:\n[^\n\r]+){0,3})",
                rf"(?i)(?:from|to)[\s\S]*?\b(?:address|location)[\s:]*([^\n\r]+(?:\n[^\n\r]+){0,3})",
            ],
            "email": [
                rf"(?i){party_type}[\s\S]*?\b(?:email|e-mail|mail)[\s:]*([\w\.-]+@[\w\.-]+\.\w+)",
                rf"(?i)(?:from|to)[\s\S]*?\b(?:email|e-mail|mail)[\s:]*([\w\.-]+@[\w\.-]+\.\w+)",
                rf"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            ],
            "tax_id": [
                rf"(?i){party_type}[\s\S]*?\b(?:tax\s*id|vat\s*id|tax\s*number|vat\s*number)[\s:]*([A-Z0-9-]+)",
                rf"(?i)(?:from|to)[\s\S]*?\b(?:tax\s*id|vat\s*id|tax\s*number|vat\s*number)[\s:]*([A-Z0-9-]+)",
                r"\b(?:VAT|TAX)[\s:]*[A-Z]{0,3}[0-9\-\s]+\b",
            ],
        }

        # Extract each field using patterns
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    # Get the first non-empty group
                    value = next((g for g in match.groups() if g), "").strip()
                    if value:
                        party[field] = value
                        break

        return party

    def _extract_table_items(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract line items from a detected table in the invoice

        This implementation uses regex patterns to identify and parse tabular data
        in the extracted text. It looks for common table structures and extracts
        line items based on header patterns.

        Args:
            text: Full text of the invoice

        Returns:
            List of line items with description, quantity, unit price, and total
        """
        items = []

        # Common table patterns
        table_patterns = [
            # Pattern for tables with borders
            r"(?s)(?<=\n\s*[+=-]+\s*\n)(.*?)(?=\n\s*[+=-]+\s*\n|\Z)",
            # Pattern for tables with line separators
            r"(?s)(?<=\n\s*[-]{20,}\s*\n)(.*?)(?=\n\s*[-]{20,}\s*\n|\Z)",
            # Pattern for tables with just whitespace separation
            r"(?s)(?<=\n\s*\n)((?:[^\n]*?\s{2,}.*?\n)+)(?=\n\s*\n|\Z)",
        ]

        # Try each pattern to find potential tables
        for pattern in table_patterns:
            table_matches = re.finditer(pattern, text, re.MULTILINE)

            for match in table_matches:
                table_text = match.group(0)
                lines = [
                    line.strip() for line in table_text.split("\n") if line.strip()
                ]

                # Skip if too few lines to be a valid table
                if len(lines) < 2:  # Need at least header + 1 data row
                    continue

                # Try to identify headers and their positions
                headers = []
                for line in lines[:2]:  # Check first two lines for headers
                    # Split on 2+ spaces or tabs
                    parts = re.split(r"\s{2,}|\t", line)
                    if parts:
                        headers = [h.lower().strip() for h in parts if h.strip()]
                        if len(headers) >= 2:  # Need at least 2 columns
                            break

                if not headers:
                    continue

                # Map headers to field types
                field_mapping = {}
                for i, header in enumerate(headers):
                    header_lower = header.lower()
                    if any(
                        p in header_lower
                        for p in ["desc", "item", "product", "service"]
                    ):
                        field_mapping[i] = "description"
                    elif any(p in header_lower for p in ["qty", "quantity", "amount"]):
                        field_mapping[i] = "quantity"
                    elif any(p in header_lower for p in ["price", "rate", "unit"]):
                        field_mapping[i] = "unit_price"
                    elif "total" in header_lower:
                        field_mapping[i] = "total"

                # If we couldn't identify enough fields, skip this table
                if len(field_mapping) < 2:
                    continue

                # Process data rows (skip header)
                for line in lines[1:]:
                    # Skip lines that look like section headers or totals
                    if re.search(
                        r"(?i)total|subtotal|balance|amount due|grand total", line
                    ):
                        continue

                    # Split the line into columns
                    columns = re.split(r"\s{2,}|\t", line.strip())
                    if len(columns) < 2:  # Need at least 2 columns
                        continue

                    # Create a new item
                    item = {}
                    valid_item = False

                    for i, col in enumerate(columns):
                        if i in field_mapping and col.strip():
                            field = field_mapping[i]
                            value = col.strip()

                            # Clean and convert values
                            if field == "quantity":
                                try:
                                    item[field] = float(
                                        re.sub(r"[^\d.]", "", value) or "1"
                                    )
                                    valid_item = True
                                except (ValueError, TypeError):
                                    item[field] = 1.0
                            elif field in ["unit_price", "total"]:
                                try:
                                    item[field] = float(
                                        re.sub(r"[^\d.]", "", value) or "0"
                                    )
                                    valid_item = True
                                except (ValueError, TypeError):
                                    item[field] = 0.0
                            else:
                                item[field] = value
                                if field == "description" and value:
                                    valid_item = True

                    # Only add if we have required fields
                    if valid_item and "description" in item:
                        # Calculate missing fields if possible
                        if (
                            "quantity" in item
                            and "unit_price" in item
                            and "total" not in item
                        ):
                            try:
                                item["total"] = item["quantity"] * item["unit_price"]
                            except (TypeError, KeyError):
                                pass
                        elif (
                            "quantity" in item
                            and "total" in item
                            and "unit_price" not in item
                            and item["quantity"] != 0
                        ):
                            try:
                                item["unit_price"] = item["total"] / item["quantity"]
                            except (TypeError, KeyError, ZeroDivisionError):
                                pass

                        # Create an InvoiceItem and add to results
                        try:
                            invoice_item = InvoiceItem()
                            invoice_item.description = item.get("description", "")
                            invoice_item.quantity = item.get("quantity", 1.0)
                            invoice_item.unit_price = item.get("unit_price", 0.0)
                            invoice_item.total = item.get("total", 0.0)

                            items.append(invoice_item.to_dict())
                        except Exception as e:
                            logger.warning(f"Error creating invoice item: {e}")

        return items

    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract line items from invoice text using table extraction or pattern matching

        Args:
            text: Full text of the invoice

        Returns:
            List of line items with description, quantity, unit price, and total
        """
        items = []

        # First try to extract items from tables
        table_items = self._extract_table_items(text)
        if table_items:
            return table_items

        # If no table items found, try pattern matching

        # If no table found, try to find line items using patterns
        if not items:
            # Look for line item patterns like "1 x Description $10.00"
            item_patterns = [
                r"(?i)(\d+)\s*[x×]\s*([^$€£¥\n]+?)\s*([$€£¥]?\s*[\d,.]+)",
                r"(?i)([^\n\r]+?)\s+(\d+)\s+[x×]?\s*[$€£¥]?\s*([\d,.]+)\s+[$€£¥]?\s*([\d,.]+)",
                r"(?i)([^\n\r]+?)\s+\b(?:Qty|Quantity)[\s:]+(\d+)[^\n\r]*?\b(?:Unit|Price)[\s:]+[$€£¥]?\s*([\d,.]+)[^\n\r]*?\b(?:Total|Amount)[\s:]+[$€£¥]?\s*([\d,.]+)",
            ]

            for pattern in item_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    try:
                        if len(match.groups()) >= 3:
                            item = InvoiceItem()
                            item.description = match.group(1).strip()
                            item.quantity = float(match.group(2).replace(",", ""))
                            item.unit_price = float(
                                match.group(3)
                                .replace(",", "")
                                .replace("$", "")
                                .replace("€", "")
                                .replace("£", "")
                                .replace("¥", "")
                            )

                            # If there's a 4th group, it's the total, otherwise calculate it
                            if len(match.groups()) >= 4:
                                item.total = float(
                                    match.group(4)
                                    .replace(",", "")
                                    .replace("$", "")
                                    .replace("€", "")
                                    .replace("£", "")
                                    .replace("¥", "")
                                )
                            else:
                                item.total = item.quantity * item.unit_price

                            items.append(item.to_dict())
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Error parsing line item: {e}")
                        continue

        return items

    def _extract_totals(self, text: str) -> Dict[str, Any]:
        """Extract total amounts from invoice"""
        totals = InvoiceTotals()

        # Try to find currency
        for pattern in self.patterns["currency"]:
            match = re.search(pattern, text)
            if match:
                totals.currency = match.group(1)
                break

        # Try to find total amount
        for pattern in self.patterns["amount"]:
            matches = re.findall(pattern, text)
            if matches:
                # Take the last match as it's likely the final total
                amount_str = matches[-1].replace(",", "")
                try:
                    totals.total = float(
                        amount_str.replace("$", "")
                        .replace("€", "")
                        .replace("£", "")
                        .replace("¥", "")
                    )
                    break
                except (ValueError, AttributeError):
                    continue

        return totals.to_dict()

    def _extract_payment_terms(self, text: str) -> str:
        """
        Extract payment terms from invoice text

        Args:
            text: Full text of the invoice

        Returns:
            Extracted payment terms or empty string if not found
        """
        # Common payment terms patterns
        patterns = [
            r"(?i)payment terms[\s:]*([^\n\r]+)",
            r"(?i)terms[\s:]*([^\n\r]+)",
            r"(?i)payment due[\s:]*([^\n\r]+)",
            r"(?i)net[\s:]*([^\n\r]+)",
            r"(?i)please pay (?:within|by)[\s:]*([^\n\r]+)",
            r"(?i)payment is due[\s:]*([^\n\r]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                terms = match.group(1).strip()
                # Clean up the extracted terms
                terms = re.sub(r"[\s\n\r]+", " ", terms).strip()
                return terms

        return ""

    def _extract_notes(self, text: str) -> str:
        """
        Extract any notes or additional information from invoice

        Args:
            text: Full text of the invoice

        Returns:
            Extracted notes or empty string if not found
        """
        # Common notes patterns
        patterns = [
            r"(?i)notes?:?[\s\n]+([\s\S]+?)(?=\n\s*\n|$)",
            r"(?i)additional information[\s\n]+([\s\S]+?)(?=\n\s*\n|$)",
            r"(?i)remarks?:?[\s\n]+([\s\S]+?)(?=\n\s*\n|$)",
            r"(?i)comments?:?[\s\n]+([\s\S]+?)(?=\n\s*\n|$)",
        ]

        notes = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    # If we have multiple groups, take the first non-empty one
                    note = next((m for m in match if m.strip()), "").strip()
                else:
                    note = match.strip()

                if note and note not in notes:
                    notes.append(note)

        # Join all notes with double newlines
        return "\n\n".join(notes) if notes else ""

    def to_json(
        self, pdf_path: Union[str, Path], output_path: Union[str, Path, None] = None
    ) -> str:
        """
        Convert PDF to JSON format

        Args:
            pdf_path: Path to the PDF file
            output_path: Optional path to save the JSON output

        Returns:
            JSON string with extracted data
        """
        data = self.extract_structured_data(pdf_path)
        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)

        return json_str


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
        self.supported_formats = ["png", "jpg", "jpeg", "tiff", "bmp"]

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
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
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
        context.update(
            {
                "current_date": "2025-06-15",
                "currency": "PLN",
                "company_logo": "",
                "formatted_totals": self._format_currency_values(
                    data.get("totals", {})
                ),
            }
        )

        return context

    def _format_currency_values(self, totals: Dict) -> Dict:
        """Format currency values for display"""
        return {
            "subtotal": f"{totals.get('subtotal', 0):.2f}",
            "tax_amount": f"{totals.get('tax_amount', 0):.2f}",
            "total": f"{totals.get('total', 0):.2f}",
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
