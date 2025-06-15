# tests/conftest.py
"""
Pytest configuration and fixtures for InvOCR tests
"""

import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from invocr.core.converter import create_converter
from invocr.core.ocr import create_ocr_engine
from invocr.core.extractor import create_extractor
from invocr.core.validator import create_validator


@pytest.fixture
def sample_invoice_data() -> Dict[str, Any]:
    """Sample invoice data for testing"""
    return {
        "document_number": "FV/2025/TEST/001",
        "document_date": "2025-06-15",
        "due_date": "2025-07-15",
        "seller": {
            "name": "Test Company Sp. z o.o.",
            "address": "ul. Testowa 123\n80-001 Gdańsk\nPolska",
            "tax_id": "123-456-78-90",
            "phone": "+48 58 123 45 67",
            "email": "test@company.pl"
        },
        "buyer": {
            "name": "Client Test Ltd.",
            "address": "Test Street 456\n12345 Test City\nPoland",
            "tax_id": "987-654-32-10",
            "phone": "+48 58 987 65 43",
            "email": "client@test.com"
        },
        "items": [
            {
                "description": "Programming services - web development",
                "quantity": 40,
                "unit_price": 150.00,
                "total_price": 6000.00
            },
            {
                "description": "IT consulting - system architecture",
                "quantity": 8,
                "unit_price": 200.00,
                "total_price": 1600.00
            }
        ],
        "totals": {
            "subtotal": 7600.00,
            "tax_rate": 23.0,
            "tax_amount": 1748.00,
            "total": 9348.00
        },
        "payment_method": "Bank transfer",
        "bank_account": "PL 12 1234 5678 9012 3456 7890 1234",
        "notes": "Payment due within 30 days."
    }


@pytest.fixture
def temp_directory():
    """Temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_text():
    """Sample OCR text for testing"""
    return """
    FAKTURA FV/2025/001
    Data wystawienia: 2025-06-15
    Termin płatności: 2025-07-15

    Sprzedawca:
    Test Company Sp. z o.o.
    ul. Testowa 123, 80-001 Gdańsk
    NIP: 123-456-78-90

    Nabywca:
    Client Test Ltd.
    Test Street 456, 12345 Test City
    NIP: 987-654-32-10

    Lp. Opis                    Ilość  Cena jedn.  Wartość
    1   Programming services    40     150,00      6000,00
    2   IT consulting          8      200,00      1600,00

    Suma netto:     7600,00 PLN
    VAT 23%:        1748,00 PLN
    Razem:          9348,00 PLN
    """


@pytest.fixture
def converter():
    """Create converter instance"""
    return create_converter(['en', 'pl'])


@pytest.fixture
def ocr_engine():
    """Create OCR engine instance"""
    return create_ocr_engine(['en', 'pl'])


@pytest.fixture
def extractor():
    """Create data extractor instance"""
    return create_extractor(['en', 'pl'])


@pytest.fixture
def validator():
    """Create validator instance"""
    return create_validator()


# ---

# tests/test_ocr.py
"""
Tests for OCR functionality
"""

import pytest
import tempfile
from pathlib import Path
from PIL import Image
import numpy as np

from invocr.core.ocr import OCREngine, create_ocr_engine


class TestOCR:
    """Test OCR engine functionality"""

    def test_create_ocr_engine(self):
        """Test OCR engine creation"""
        engine = create_ocr_engine(['en', 'pl'])
        assert isinstance(engine, OCREngine)
        assert 'en' in engine.languages
        assert 'pl' in engine.languages

    def test_language_mapping(self):
        """Test language code mapping"""
        engine = create_ocr_engine(['en', 'pl', 'de'])
        mapped = engine._map_languages(['en', 'pl', 'de'])
        assert 'eng' in mapped
        assert 'pol' in mapped
        assert 'deu' in mapped

    def test_language_detection(self):
        """Test language detection"""
        engine = create_ocr_engine()

        # Polish text
        assert engine.detect_language("Faktura z dnia dzisiejszego ąćęłńóśźż") == 'pl'

        # German text
        assert engine.detect_language("Rechnung für größe Bestellung") == 'de'

        # English text (default)
        assert engine.detect_language("Invoice for services") == 'en'

    def test_image_preprocessing(self, temp_directory):
        """Test image preprocessing"""
        engine = create_ocr_engine()

        # Create simple test image
        img_array = np.ones((100, 100, 3), dtype=np.uint8) * 255
        img = Image.fromarray(img_array)
        img_path = temp_directory / "test.png"
        img.save(img_path)

        # Test preprocessing
        processed = engine._load_and_preprocess(img_path)
        assert processed is not None
        assert len(processed.shape) == 2  # Should be grayscale

    @pytest.mark.skipif(
        True,  # Skip by default as requires OCR engines
        reason="Requires OCR engines installed"
    )
    def test_text_extraction(self, temp_directory):
        """Test text extraction from image"""
        engine = create_ocr_engine(['en'])

        # Create test image with text (would need actual text image)
        # This is a placeholder test
        img_path = temp_directory / "test_text.png"

        # Skip if no test image available
        if not img_path.exists():
            pytest.skip("No test image available")

        result = engine.extract_text(img_path)
        assert "text" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1

    def test_enhance_image_quality(self, temp_directory):
        """Test image quality enhancement"""
        engine = create_ocr_engine()

        # Create test image
        img_array = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)
        img_path = temp_directory / "test.png"
        img.save(img_path)

        # Test enhancement
        enhanced_path = engine.enhance_image_quality(img_path)
        assert Path(enhanced_path).exists()

        # Check if enhanced image is larger (upscaled)
        with Image.open(enhanced_path) as enhanced:
            assert enhanced.size[0] >= 1000 or enhanced.size[1] >= 1000


# ---

# tests/test_converter.py
"""
Tests for format conversion functionality
"""

import pytest
import json
from pathlib import Path

from invocr.core.converter import UniversalConverter, create_converter


class TestConverter:
    """Test converter functionality"""

    def test_create_converter(self):
        """Test converter creation"""
        converter = create_converter(['en', 'pl'])
        assert isinstance(converter, UniversalConverter)
        assert 'en' in converter.languages
        assert 'pl' in converter.languages

    def test_format_detection(self):
        """Test automatic format detection"""
        converter = create_converter()

        assert converter._detect_format("test.pdf") == "pdf"
        assert converter._detect_format("test.png") == "image"
        assert converter._detect_format("test.jpg") == "image"
        assert converter._detect_format("test.json") == "json"
        assert converter._detect_format("test.xml") == "xml"
        assert converter._detect_format("test.html") == "html"
        assert converter._detect_format("test.unknown") == "unknown"

    def test_json_to_xml_conversion(self, converter, sample_invoice_data):
        """Test JSON to XML conversion"""
        xml_content = converter.json_to_xml(sample_invoice_data)

        assert isinstance(xml_content, str)
        assert xml_content.startswith('<?xml')
        assert "Invoice" in xml_content
        assert sample_invoice_data["document_number"] in xml_content
        assert "InvoiceLines" in xml_content

    def test_json_to_html_conversion(self, converter, sample_invoice_data):
        """Test JSON to HTML conversion"""
        html_content = converter.json_to_html(sample_invoice_data)

        assert isinstance(html_content, str)
        assert html_content.startswith('<!DOCTYPE html>')
        assert sample_invoice_data["document_number"] in html_content
        assert sample_invoice_data["seller"]["name"] in html_content
        assert sample_invoice_data["buyer"]["name"] in html_content

    def test_load_save_data(self, converter, sample_invoice_data, temp_directory):
        """Test data loading and saving"""
        # Test JSON loading
        json_file = temp_directory / "test.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(sample_invoice_data, f)

        loaded_data = converter._load_data(json_file, "json")
        assert loaded_data["document_number"] == sample_invoice_data["document_number"]

        # Test data saving
        output_file = temp_directory / "output.json"
        result = converter._save_data(sample_invoice_data, output_file, "json")

        assert output_file.exists()
        assert "size" in result

        # Verify saved content
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data["document_number"] == sample_invoice_data["document_number"]

    @pytest.mark.skipif(
        True,  # Skip by default as requires WeasyPrint dependencies
        reason="Requires WeasyPrint system dependencies"
    )
    def test_html_to_pdf_conversion(self, converter, sample_invoice_data, temp_directory):
        """Test HTML to PDF conversion"""
        # Generate HTML
        html_content = converter.json_to_html(sample_invoice_data)

        # Save to file
        html_file = temp_directory / "test.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Convert to PDF
        pdf_file = temp_directory / "test.pdf"
        converter.html_to_pdf(html_file, pdf_file)

        assert pdf_file.exists()
        assert pdf_file.stat().st_size > 1000  # PDF should be at least 1KB


# ---

# tests/test_api.py
"""
Tests for REST API functionality
"""

import pytest
import json
from fastapi.testclient import TestClient

from invocr.api.main import app


class TestAPI:
    """Test API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "InvOCR" in data["message"]

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data

    def test_info_endpoint(self, client):
        """Test system info endpoint"""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "supported_formats" in data
        assert "supported_languages" in data
        assert "features" in data

    @pytest.mark.asyncio
    async def test_convert_endpoint_validation(self, client):
        """Test convert endpoint validation"""
        # Test without file
        response = client.post("/convert")
        assert response.status_code == 422  # Validation error

    def test_status_endpoint_not_found(self, client):
        """Test status endpoint with non-existent job"""
        response = client.get("/status/non-existent-job")
        assert response.status_code == 404

    def test_download_endpoint_not_found(self, client):
        """Test download endpoint with non-existent job"""
        response = client.get("/download/non-existent-job")
        assert response.status_code == 404


# ---

# tests/test_extractor.py
"""
Tests for data extraction functionality
"""

import pytest
from invocr.core.extractor import DataExtractor, create_extractor


class TestExtractor:
    """Test data extractor functionality"""

    def test_create_extractor(self):
        """Test extractor creation"""
        extractor = create_extractor(['en', 'pl'])
        assert isinstance(extractor, DataExtractor)
        assert 'en' in extractor.languages
        assert 'pl' in extractor.languages

    def test_language_detection(self, extractor):
        """Test language detection"""
        # Polish text
        polish_text = "Faktura VAT sprzedawca nabywca płatność"
        assert extractor._detect_language(polish_text) == 'pl'

        # English text
        english_text = "Invoice VAT seller buyer payment"
        assert extractor._detect_language(english_text) == 'en'

        # German text
        german_text = "Rechnung Verkäufer Käufer Zahlung"
        assert extractor._detect_language(german_text) == 'de'

    def test_extract_invoice_data(self, extractor, sample_text):
        """Test invoice data extraction"""
        result = extractor.extract_invoice_data(sample_text, "invoice")

        assert isinstance(result, dict)
        assert "document_number" in result
        assert "seller" in result
        assert "buyer" in result
        assert "items" in result
        assert "totals" in result
        assert "_metadata" in result

        # Check specific extractions
        assert "FV/2025/001" in result["document_number"]
        assert len(result["items"]) > 0

        # Check metadata
        metadata = result["_metadata"]
        assert "document_type" in metadata
        assert "detected_language" in metadata
        assert "extraction_timestamp" in metadata

    def test_extract_dates(self, extractor):
        """Test date extraction"""
        text = "Data: 2025-06-15 Termin: 15/07/2025"
        dates = extractor._extract_dates(text)

        assert len(dates) >= 1
        assert "2025-06-15" in dates or "2025-07-15" in dates

    def test_extract_tax_ids(self, extractor):
        """Test tax ID extraction"""
        text = "NIP: 123-456-78-90 VAT ID: 987654321"
        tax_ids = extractor._extract_tax_ids(text)

        assert len(tax_ids) >= 1
        assert any("123" in tax_id for tax_id in tax_ids)

    def test_extract_emails(self, extractor):
        """Test email extraction"""
        text = "Contact: test@company.com or support@example.org"
        emails = extractor._extract_emails(text)

        assert len(emails) >= 1
        assert "test@company.com" in emails

    def test_extract_phones(self, extractor):
        """Test phone number extraction"""
        text = "Tel: +48 58 123 45 67 or 123-456-789"
        phones = extractor._extract_phones(text)

        assert len(phones) >= 1

    def test_calculate_confidence(self, extractor, sample_invoice_data):
        """Test confidence calculation"""
        confidence = extractor._calculate_confidence(sample_invoice_data, "sample text")

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high for complete data


# ---

# tests/test_validator.py
"""
Tests for data validation functionality
"""

import pytest
from invocr.core.validator import InvoiceValidator, create_validator, ValidationError


class TestValidator:
    """Test validator functionality"""

    def test_create_validator(self):
        """Test validator creation"""
        validator = create_validator()
        assert isinstance(validator, InvoiceValidator)

    def test_validate_complete_data(self, validator, sample_invoice_data):
        """Test validation of complete, valid data"""
        result = validator.validate(sample_invoice_data)

        assert result.is_valid or len(result.errors) == 0
        assert result.quality_score > 0.8
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.suggestions, list)

    def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields"""
        incomplete_data = {
            "document_number": "TEST/001"
            # Missing other required fields
        }

        result = validator.validate(incomplete_data)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert result.quality_score < 0.5

        # Check for specific missing fields
        error_fields = [error.field for error in result.errors]
        assert "seller" in error_fields
        assert "buyer" in error_fields
        assert "items" in error_fields
        assert "totals" in error_fields

    def test_validate_invalid_data_types(self, validator):
        """Test validation with invalid data types"""
        invalid_data = {
            "document_number": 123,  # Should be string
            "seller": "not a dict",  # Should be dict
            "items": "not a list",  # Should be list
            "totals": []  # Should be dict
        }

        result = validator.validate(invalid_data)

        assert not result.is_valid
        assert len(result.errors) > 0

        # Check for type validation errors
        error_messages = [error.message for error in result.errors]
        assert any("must be a dictionary" in msg for msg in error_messages)

    def test_validate_dates(self, validator):
        """Test date validation"""
        # Future date
        future_data = {
            "document_number": "TEST/001",
            "document_date": "2030-01-01",
            "seller": {"name": "Test"},
            "buyer": {"name": "Test"},
            "items": [{"description": "Test", "quantity": 1, "unit_price": 100, "total_price": 100}],
            "totals": {"total": 100}
        }

        result = validator.validate(future_data)
        warning_messages = [w.message for w in result.warnings]
        assert any("future" in msg.lower() for msg in warning_messages)

        # Due date before document date
        invalid_dates = future_data.copy()
        invalid_dates["due_date"] = "2029-01-01"  # Before document date

        result = validator.validate(invalid_dates)
        error_messages = [e.message for e in result.errors]
        assert any("due date" in msg.lower() and "before" in msg.lower() for msg in error_messages)

    def test_validate_items(self, validator):
        """Test item validation"""
        data_with_items = {
            "document_number": "TEST/001",
            "seller": {"name": "Test"},
            "buyer": {"name": "Test"},
            "items": [
                {
                    "description": "Valid item",
                    "quantity": 2,
                    "unit_price": 50.0,
                    "total_price": 100.0
                },
                {
                    "description": "",  # Invalid: empty description
                    "quantity": -1,  # Invalid: negative quantity
                    "unit_price": "not a number",  # Invalid: not numeric
                    "total_price": 50.0
                }
            ],
            "totals": {"total": 150}
        }

        result = validator.validate(data_with_items)

        assert len(result.errors) > 0
        error_messages = [e.message for e in result.errors]
        assert any("must be positive" in msg for msg in error_messages)
        assert any("must be a number" in msg for msg in error_messages)

    def test_validate_totals_calculation(self, validator):
        """Test totals validation against items"""
        data_with_wrong_totals = {
            "document_number": "TEST/001",
            "seller": {"name": "Test"},
            "buyer": {"name": "Test"},
            "items": [
                {
                    "description": "Item 1",
                    "quantity": 2,
                    "unit_price": 50.0,
                    "total_price": 100.0
                }
            ],
            "totals": {
                "subtotal": 200.0,  # Wrong: should be 100.0
                "total": 200.0
            }
        }

        result = validator.validate(data_with_wrong_totals)

        warning_messages = [w.message for w in result.warnings]
        assert any("doesn't match" in msg.lower() for msg in warning_messages)

    def test_validate_tax_ids(self, validator):
        """Test tax ID validation"""
        data_with_tax_ids = {
            "document_number": "TEST/001",
            "seller": {
                "name": "Test Seller",
                "tax_id": "abc-def-gh-ij"  # Invalid: non-numeric
            },
            "buyer": {
                "name": "Test Buyer",
                "tax_id": "12345"  # Warning: too short
            },
            "items": [{"description": "Test", "quantity": 1, "unit_price": 100, "total_price": 100}],
            "totals": {"total": 100}
        }

        result = validator.validate(data_with_tax_ids)

        warning_messages = [w.message for w in result.warnings]
        assert any("non-numeric" in msg.lower() for msg in warning_messages)
        assert any("too short" in msg.lower() for msg in warning_messages)

    def test_quick_validation(self, validator, sample_invoice_data):
        """Test quick validation method"""
        # Valid data
        assert validator.validate_quick(sample_invoice_data) == True

        # Invalid data
        assert validator.validate_quick({}) == False
        assert validator.validate_quick("not a dict") == False
        assert validator.validate_quick({"document_number": "TEST"}) == False  # Missing items, totals

    def test_validation_summary(self, validator, sample_invoice_data):
        """Test validation summary generation"""
        result = validator.validate(sample_invoice_data)
        summary = validator.get_validation_summary(result)

        assert isinstance(summary, str)
        assert "Quality score" in summary

        if result.is_valid:
            assert "✅" in summary
        else:
            assert "❌" in summary

    def test_email_validation(self, validator):
        """Test email validation"""
        # Valid emails
        assert validator._is_valid_email("test@example.com") == True
        assert validator._is_valid_email("user.name@domain.co.uk") == True

        # Invalid emails
        assert validator._is_valid_email("invalid.email") == False
        assert validator._is_valid_email("@domain.com") == False
        assert validator._is_valid_email("test@") == False


# ---

# tests/test_formats.py
"""
Tests for format handlers
"""

import pytest
import tempfile
from pathlib import Path
from PIL import Image
import numpy as np

from invocr.formats.pdf import PDFProcessor
from invocr.formats.image import ImageProcessor
from invocr.formats.json_handler import JSONHandler
from invocr.formats.xml_handler import XMLHandler
from invocr.formats.html_handler import HTMLHandler


class TestPDFProcessor:
    """Test PDF processing functionality"""

    def test_pdf_processor_creation(self):
        """Test PDF processor creation"""
        processor = PDFProcessor()
        assert 'png' in processor.supported_formats
        assert 'jpg' in processor.supported_formats

    @pytest.mark.skipif(
        True,  # Skip by default as requires PDF files
        reason="Requires test PDF files"
    )
    def test_extract_text(self, temp_directory):
        """Test PDF text extraction"""
        processor = PDFProcessor()

        # Would need actual PDF file for testing
        pdf_path = temp_directory / "test.pdf"
        if not pdf_path.exists():
            pytest.skip("No test PDF available")

        text = processor.extract_text(pdf_path)
        assert isinstance(text, str)


class TestImageProcessor:
    """Test image processing functionality"""

    def test_image_processor_creation(self):
        """Test image processor creation"""
        processor = ImageProcessor()
        assert 'png' in processor.supported_formats
        assert 'jpg' in processor.supported_formats

    def test_preprocess_for_ocr(self, temp_directory):
        """Test image preprocessing"""
        processor = ImageProcessor()

        # Create test image
        img_array = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)
        img_path = temp_directory / "test.png"
        img.save(img_path)

        # Test preprocessing
        processed = processor.preprocess_for_ocr(img_path)
        assert processed is not None
        assert len(processed.shape) == 2  # Should be grayscale

    def test_enhance_image_quality(self, temp_directory):
        """Test image quality enhancement"""
        processor = ImageProcessor()

        # Create small test image
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)
        img_path = temp_directory / "small_test.png"
        img.save(img_path)

        # Test enhancement
        enhanced_path = processor.enhance_image_quality(img_path)
        assert Path(enhanced_path).exists()

        # Check if enhanced image is larger
        with Image.open(enhanced_path) as enhanced:
            assert enhanced.size[0] >= 1000 or enhanced.size[1] >= 1000

    def test_get_image_info(self, temp_directory):
        """Test image info extraction"""
        processor = ImageProcessor()

        # Create test image
        img = Image.new('RGB', (300, 200), color='red')
        img_path = temp_directory / "info_test.png"
        img.save(img_path)

        info = processor.get_image_info(img_path)
        assert info["width"] == 300
        assert info["height"] == 200
        assert info["format"] == "PNG"


class TestJSONHandler:
    """Test JSON handler functionality"""

    def test_json_handler_creation(self):
        """Test JSON handler creation"""
        handler = JSONHandler()
        assert handler.schema_version == "1.0"

    def test_load_save_json(self, temp_directory, sample_invoice_data):
        """Test JSON loading and saving"""
        handler = JSONHandler()

        # Test save
        json_file = temp_directory / "test.json"
        success = handler.save(sample_invoice_data, json_file)
        assert success == True
        assert json_file.exists()

        # Test load
        loaded_data = handler.load(json_file)
        assert loaded_data["document_number"] == sample_invoice_data["document_number"]
        assert "_metadata" in loaded_data  # Should be added during save

    def test_validate_json(self, sample_invoice_data):
        """Test JSON validation"""
        handler = JSONHandler()

        # Valid data
        assert handler.validate(sample_invoice_data) == True

        # Invalid data (missing required fields)
        invalid_data = {"document_number": "TEST"}
        assert handler.validate(invalid_data) == False


class TestXMLHandler:
    """Test XML handler functionality"""

    def test_xml_handler_creation(self):
        """Test XML handler creation"""
        handler = XMLHandler()
        assert "eu_invoice" in handler.namespaces

    def test_json_to_xml(self, sample_invoice_data):
        """Test JSON to XML conversion"""
        handler = XMLHandler()

        xml_content = handler.to_xml(sample_invoice_data, "eu_invoice")

        assert isinstance(xml_content, str)
        assert xml_content.startswith('<?xml')
        assert "<Invoice" in xml_content
        assert sample_invoice_data["document_number"] in xml_content
        assert "InvoiceLines" in xml_content
        assert "SellerParty" in xml_content
        assert "BuyerParty" in xml_content

    def test_generic_xml(self, sample_invoice_data):
        """Test generic XML format"""
        handler = XMLHandler()

        xml_content = handler.to_xml(sample_invoice_data, "generic")

        assert isinstance(xml_content, str)
        assert xml_content.startswith('<?xml')
        assert "<Invoice>" in xml_content


class TestHTMLHandler:
    """Test HTML handler functionality"""

    def test_html_handler_creation(self):
        """Test HTML handler creation"""
        handler = HTMLHandler()
        assert "modern" in handler.templates
        assert "classic" in handler.templates
        assert "minimal" in handler.templates

    def test_json_to_html(self, sample_invoice_data):
        """Test JSON to HTML conversion"""
        handler = HTMLHandler()

        # Test different templates
        for template_name in ["modern", "classic", "minimal"]:
            html_content = handler.to_html(sample_invoice_data, template_name)

            assert isinstance(html_content, str)
            assert html_content.startswith('<!DOCTYPE html>')
            assert sample_invoice_data["document_number"] in html_content
            assert sample_invoice_data["seller"]["name"] in html_content

    def test_context_preparation(self, sample_invoice_data):
        """Test template context preparation"""
        handler = HTMLHandler()

        context = handler._prepare_context(sample_invoice_data)

        assert "current_date" in context
        assert "currency" in context
        assert "formatted_totals" in context
        assert context["document_number"] == sample_invoice_data["document_number"]

    def test_currency_formatting(self, sample_invoice_data):
        """Test currency value formatting"""
        handler = HTMLHandler()

        formatted = handler._format_currency_values(sample_invoice_data["totals"])

        assert "subtotal" in formatted
        assert "tax_amount" in formatted
        assert "total" in formatted
        assert "7600.00" in formatted["subtotal"]
        assert "9348.00" in formatted["total"]


# ---

# tests/test_integration.py
"""
Integration tests for complete workflows
"""

import pytest
import json
from pathlib import Path

from invocr.core.converter import create_converter


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_json_to_formats_pipeline(self, sample_invoice_data, temp_directory):
        """Test complete JSON to other formats pipeline"""
        converter = create_converter()

        # JSON → XML
        xml_content = converter.json_to_xml(sample_invoice_data)
        xml_file = temp_directory / "test.xml"
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        assert xml_file.exists()

        # JSON → HTML
        html_content = converter.json_to_html(sample_invoice_data)
        html_file = temp_directory / "test.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        assert html_file.exists()

        # Verify content quality
        assert sample_invoice_data["document_number"] in xml_content
        assert sample_invoice_data["document_number"] in html_content
        assert len(xml_content) > 1000  # Reasonable size
        assert len(html_content) > 2000  # HTML should be larger

    def test_data_consistency(self, sample_invoice_data, temp_directory):
        """Test data consistency across formats"""
        converter = create_converter()

        # Save original JSON
        json_file = temp_directory / "original.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(sample_invoice_data, f, ensure_ascii=False, indent=2)

        # Convert JSON → XML → back to dict (simplified)
        xml_content = converter.json_to_xml(sample_invoice_data)
        # Note: Full XML→JSON conversion would require XML parser implementation

        # Convert JSON → HTML
        html_content = converter.json_to_html(sample_invoice_data)

        # Verify key data is preserved
        assert sample_invoice_data["document_number"] in xml_content
        assert sample_invoice_data["document_number"] in html_content
        assert str(sample_invoice_data["totals"]["total"]) in html_content

    @pytest.mark.asyncio
    async def test_error_handling_pipeline(self, temp_directory):
        """Test error handling in conversion pipeline"""
        converter = create_converter()

        # Test with invalid/empty data
        empty_data = {}

        try:
            xml_content = converter.json_to_xml(empty_data)
            # Should handle gracefully
            assert isinstance(xml_content, str)
        except Exception as e:
            # Or raise appropriate exception
            assert "error" in str(e).lower() or "invalid" in str(e).lower()

        try:
            html_content = converter.json_to_html(empty_data)
            assert isinstance(html_content, str)
        except Exception as e:
            assert "error" in str(e).lower() or "invalid" in str(e).lower()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])