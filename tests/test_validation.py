"""
Tests for the validation utilities.
"""

import os
import pytest
import json
import decimal
from datetime import date, datetime
from pathlib import Path
from invocr.utils.validation import (
    safe_json_dumps,
    safe_json_loads,
    sanitize_input,
    validate_file_extension,
    is_valid_pdf,
    is_valid_pdf_simple
)

class TestSafeJsonSerialization:
    def test_serialize_datetime(self):
        """Test serialization of datetime objects."""
        test_date = datetime(2023, 1, 1, 12, 0, 0)
        result = safe_json_dumps({"date": test_date})
        assert "2023-01-01T12:00:00" in result

    def test_serialize_decimal(self):
        """Test serialization of Decimal objects."""
        test_decimal = decimal.Decimal("123.45")
        result = safe_json_dumps({"amount": test_decimal})
        assert "123.45" in result
        assert json.loads(result)["amount"] == 123.45

    def test_roundtrip(self):
        """Test that serialization and deserialization work together."""
        data = {
            "date": datetime(2023, 1, 1),
            "amount": decimal.Decimal("123.45"),
            "text": "test"
        }
        serialized = safe_json_dumps(data)
        deserialized = safe_json_loads(serialized)
        assert deserialized["text"] == "test"
        assert deserialized["amount"] == 123.45

class TestSanitizeInput:
    def test_sanitize_string(self):
        """Test sanitization of string input."""
        test_input = "<script>alert('xss')</script>"
        result = sanitize_input(test_input)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_dict(self):
        """Test sanitization of dictionary input."""
        test_input = {"key": "<value>"}
        result = sanitize_input(test_input)
        assert "<value>" not in result
        assert "&lt;value&gt;" in result

    def test_max_length(self):
        """Test maximum length enforcement."""
        test_input = "a" * 100
        with pytest.raises(ValueError):
            sanitize_input(test_input, max_length=50)

class TestFileValidation:
    def test_validate_file_extension(self, tmp_path):
        """Test file extension validation."""
        # Test valid extension
        valid, msg = validate_file_extension("test.pdf", {".pdf", ".jpg"})
        assert valid is True
        assert msg is None

        # Test invalid extension
        valid, msg = validate_file_extension("test.txt", {".pdf", ".jpg"})
        assert valid is False
        assert "not allowed" in msg

        # Test case insensitivity
        valid, msg = validate_file_extension("test.PDF", {".pdf"})
        assert valid is True

    def test_is_valid_pdf_simple(self, tmp_path):
        """Test simple PDF validation."""
        # Create a simple PDF file
        pdf_path = tmp_path / "test.pdf"
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<<>>\nendobj\n")
        
        assert is_valid_pdf_simple(str(pdf_path)) is True

    def test_is_valid_pdf(self, tmp_path):
        """Test comprehensive PDF validation."""
        # Create a simple PDF file
        pdf_path = tmp_path / "test.pdf"
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<<>>\nendobj\n")
        
        # Test valid PDF
        valid, msg = is_valid_pdf(str(pdf_path))
        assert valid is True
        assert msg is None

        # Test non-existent file
        valid, msg = is_valid_pdf("nonexistent.pdf")
        assert valid is False
        assert "does not exist" in msg

        # Test with minimum size
        valid, msg = is_valid_pdf(str(pdf_path), min_size=1000)
        assert valid is False
        assert "too small" in msg
