"""
Unit tests for the regex extractor and validation module.

This module contains tests for the specialized regex extractor and validation
functionality to ensure they work correctly.
"""

import unittest
from decimal import Decimal
from datetime import datetime

from invocr.formats.pdf.extractors.specialized.validation import ValidationRules, DataValidator
from invocr.formats.pdf.extractors.specialized.regex_extractor import RegexExtractor, ExtractionPattern


class TestValidationRules(unittest.TestCase):
    """Test cases for the ValidationRules class."""
    
    def test_validate_percentage(self):
        """Test percentage validation."""
        # Valid percentages
        self.assertTrue(ValidationRules.validate_percentage("50%"))
        self.assertTrue(ValidationRules.validate_percentage("0%"))
        self.assertTrue(ValidationRules.validate_percentage("100%"))
        self.assertTrue(ValidationRules.validate_percentage("23.45%"))
        self.assertTrue(ValidationRules.validate_percentage(50))
        self.assertTrue(ValidationRules.validate_percentage(0))
        self.assertTrue(ValidationRules.validate_percentage(100))
        self.assertTrue(ValidationRules.validate_percentage(23.45))
        self.assertTrue(ValidationRules.validate_percentage(Decimal("50")))
        
        # Invalid percentages
        self.assertFalse(ValidationRules.validate_percentage("101%"))
        self.assertFalse(ValidationRules.validate_percentage("-1%"))
        self.assertFalse(ValidationRules.validate_percentage("abc"))
        self.assertFalse(ValidationRules.validate_percentage("50%%"))
        self.assertFalse(ValidationRules.validate_percentage(101))
        self.assertFalse(ValidationRules.validate_percentage(-1))
        self.assertFalse(ValidationRules.validate_percentage(None))
    
    def test_validate_currency_amount(self):
        """Test currency amount validation."""
        # Valid currency amounts
        self.assertTrue(ValidationRules.validate_currency_amount("100.00"))
        self.assertTrue(ValidationRules.validate_currency_amount("$100.00"))
        self.assertTrue(ValidationRules.validate_currency_amount("€100,00"))
        self.assertTrue(ValidationRules.validate_currency_amount("1,234.56"))
        self.assertTrue(ValidationRules.validate_currency_amount("-100.00"))
        self.assertTrue(ValidationRules.validate_currency_amount(100))
        self.assertTrue(ValidationRules.validate_currency_amount(100.00))
        self.assertTrue(ValidationRules.validate_currency_amount(Decimal("100.00")))
        self.assertTrue(ValidationRules.validate_currency_amount("100.1234"))  # Max 4 decimal places
        
        # Invalid currency amounts
        self.assertFalse(ValidationRules.validate_currency_amount("100.12345"))  # Too many decimal places
        self.assertFalse(ValidationRules.validate_currency_amount("abc"))
        self.assertFalse(ValidationRules.validate_currency_amount("$100.00$"))
        self.assertFalse(ValidationRules.validate_currency_amount(None))
    
    def test_validate_date(self):
        """Test date validation."""
        # Valid dates
        self.assertTrue(ValidationRules.validate_date("2023-01-01"))
        self.assertTrue(ValidationRules.validate_date("01-01-2023"))
        self.assertTrue(ValidationRules.validate_date("01/01/2023"))
        self.assertTrue(ValidationRules.validate_date("01.01.2023"))
        self.assertTrue(ValidationRules.validate_date("01 Jan 2023"))
        self.assertTrue(ValidationRules.validate_date("01 January 2023"))
        self.assertTrue(ValidationRules.validate_date(datetime.now()))
        
        # Invalid dates
        self.assertFalse(ValidationRules.validate_date("2023-13-01"))  # Invalid month
        self.assertFalse(ValidationRules.validate_date("01-32-2023"))  # Invalid day
        self.assertFalse(ValidationRules.validate_date("abc"))
        self.assertFalse(ValidationRules.validate_date("01-01-23"))  # Ambiguous year
        self.assertFalse(ValidationRules.validate_date(None))
        self.assertFalse(ValidationRules.validate_date(123))
    
    def test_validate_tax_id(self):
        """Test tax ID validation."""
        # Valid tax IDs
        self.assertTrue(ValidationRules.validate_tax_id("1234567890", "PL"))  # Polish NIP
        self.assertTrue(ValidationRules.validate_tax_id("12345678901", "DE"))  # German tax ID
        self.assertTrue(ValidationRules.validate_tax_id("12345678901234", "FR"))  # French SIRET
        self.assertTrue(ValidationRules.validate_tax_id("ABC123456"))  # Generic
        
        # Invalid tax IDs
        self.assertFalse(ValidationRules.validate_tax_id("123456789", "PL"))  # Too short for Polish NIP
        self.assertFalse(ValidationRules.validate_tax_id("1234567890A", "DE"))  # Contains letter for German tax ID
        self.assertFalse(ValidationRules.validate_tax_id("ABC12"))  # Too short for generic
        self.assertFalse(ValidationRules.validate_tax_id(None))
        self.assertFalse(ValidationRules.validate_tax_id(123))
    
    def test_validate_phone_number(self):
        """Test phone number validation."""
        # Valid phone numbers
        self.assertTrue(ValidationRules.validate_phone_number("+48123456789"))
        self.assertTrue(ValidationRules.validate_phone_number("123-456-7890"))
        self.assertTrue(ValidationRules.validate_phone_number("(123) 456 7890"))
        self.assertTrue(ValidationRules.validate_phone_number("123.456.7890"))
        
        # Invalid phone numbers
        self.assertFalse(ValidationRules.validate_phone_number("123"))  # Too short
        self.assertFalse(ValidationRules.validate_phone_number("abc"))
        self.assertFalse(ValidationRules.validate_phone_number(None))
        self.assertFalse(ValidationRules.validate_phone_number(123))
    
    def test_validate_email(self):
        """Test email validation."""
        # Valid emails
        self.assertTrue(ValidationRules.validate_email("test@example.com"))
        self.assertTrue(ValidationRules.validate_email("test.user@example.co.uk"))
        self.assertTrue(ValidationRules.validate_email("test_user123@example.org"))
        
        # Invalid emails
        self.assertFalse(ValidationRules.validate_email("test@"))
        self.assertFalse(ValidationRules.validate_email("@example.com"))
        self.assertFalse(ValidationRules.validate_email("test@example"))
        self.assertFalse(ValidationRules.validate_email("test@.com"))
        self.assertFalse(ValidationRules.validate_email("test@example."))
        self.assertFalse(ValidationRules.validate_email("test example.com"))
        self.assertFalse(ValidationRules.validate_email(None))
        self.assertFalse(ValidationRules.validate_email(123))


class TestDataValidator(unittest.TestCase):
    """Test cases for the DataValidator class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.validator = DataValidator()
    
    def test_validate_field(self):
        """Test field validation."""
        # Valid fields
        self.assertTrue(self.validator.validate_field("tax_rate", "23%", "percentage")["valid"])
        self.assertTrue(self.validator.validate_field("total", "100.00", "currency")["valid"])
        self.assertTrue(self.validator.validate_field("date", "2023-01-01", "date")["valid"])
        
        # Invalid fields
        self.assertFalse(self.validator.validate_field("tax_rate", "101%", "percentage")["valid"])
        self.assertFalse(self.validator.validate_field("total", "abc", "currency")["valid"])
        self.assertFalse(self.validator.validate_field("date", "abc", "date")["valid"])
        
        # Unknown field type
        result = self.validator.validate_field("field", "value", "unknown_type")
        self.assertFalse(result["valid"])
        self.assertIn("Unknown field type", result["error"])
    
    def test_validate_document_data(self):
        """Test document data validation."""
        data = {
            "tax_rate": "23%",
            "total_amount": "100.00",
            "issue_date": "2023-01-01",
            "invalid_field": "abc"
        }
        
        field_types = {
            "tax_rate": "percentage",
            "total_amount": "currency",
            "issue_date": "date",
            "invalid_field": "currency"
        }
        
        result = self.validator.validate_document_data(data, field_types)
        
        # Overall validation should fail due to invalid_field
        self.assertFalse(result["valid"])
        
        # Individual field validations
        self.assertTrue(result["fields"]["tax_rate"]["valid"])
        self.assertTrue(result["fields"]["total_amount"]["valid"])
        self.assertTrue(result["fields"]["issue_date"]["valid"])
        self.assertFalse(result["fields"]["invalid_field"]["valid"])
    
    def test_validate_totals_consistency(self):
        """Test totals consistency validation."""
        # Valid data with matching totals
        valid_data = {
            "line_items": [
                {"amount": "50.00"},
                {"amount": "30.00"},
                {"amount": "20.00"}
            ],
            "total_amount": "100.00"
        }
        
        result = self.validator.validate_totals_consistency(valid_data)
        self.assertTrue(result["valid"])
        
        # Invalid data with mismatched totals
        invalid_data = {
            "line_items": [
                {"amount": "50.00"},
                {"amount": "30.00"},
                {"amount": "20.00"}
            ],
            "total_amount": "110.00"
        }
        
        result = self.validator.validate_totals_consistency(invalid_data)
        self.assertFalse(result["valid"])
        
        # Data with no line items
        no_items_data = {
            "total_amount": "100.00"
        }
        
        result = self.validator.validate_totals_consistency(no_items_data)
        self.assertFalse(result["valid"])
        self.assertIn("No line items found", result["errors"])
    
    def test_register_custom_validator(self):
        """Test registering a custom validator."""
        # Define a custom validator
        def validate_postal_code(value):
            if not isinstance(value, str):
                return False
            return bool(value.isdigit() and len(value) == 5)
        
        # Register the custom validator
        self.validator.register_custom_validator("postal_code", validate_postal_code)
        
        # Test the custom validator
        self.assertTrue(self.validator.validate_field("zip", "12345", "postal_code")["valid"])
        self.assertFalse(self.validator.validate_field("zip", "1234", "postal_code")["valid"])
        self.assertFalse(self.validator.validate_field("zip", "abcde", "postal_code")["valid"])


class TestRegexExtractor(unittest.TestCase):
    """Test cases for the RegexExtractor class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.extractor = RegexExtractor()
    
    def test_extract_field(self):
        """Test extracting a field using regex patterns."""
        # Test invoice number extraction
        text = "Invoice No: INV-12345\nDate: 2023-01-01"
        value, info = self.extractor.extract_field(text, "invoice_number")
        self.assertEqual(value, "INV-12345")
        self.assertTrue(info["success"])
        
        # Test date extraction
        value, info = self.extractor.extract_field(text, "issue_date")
        self.assertIsNone(value)  # Date format doesn't match pattern
        self.assertFalse(info["success"])
        
        # Test with a different date format
        text = "Invoice No: INV-12345\nDate: 01/01/2023"
        value, info = self.extractor.extract_field(text, "issue_date")
        self.assertEqual(value, "01/01/2023")
        self.assertTrue(info["success"])
        
        # Test non-existent field
        value, info = self.extractor.extract_field(text, "non_existent_field")
        self.assertIsNone(value)
        self.assertFalse(info["success"])
        self.assertIn("No pattern defined", info["error"])
    
    def test_extract_data(self):
        """Test extracting all data from a document."""
        text = """
        INVOICE
        
        Invoice No: INV-12345
        Date: 01/01/2023
        Due Date: 31/01/2023
        
        Vendor: ACME Corporation
        Tax ID: 1234567890
        
        Customer: John Doe
        
        Items:
        1 Widget A 10.00 23% 12.30
        2 Widget B 15.00 23% 36.90
        
        Subtotal: 47.00
        Tax (23%): 10.81
        Total: 57.81
        
        Currency: USD
        """
        
        results = self.extractor.extract_data(text)
        
        # Check extracted fields
        self.assertEqual(results["invoice_number"], "INV-12345")
        self.assertEqual(results["issue_date"], "01/01/2023")
        self.assertEqual(results["due_date"], "31/01/2023")
        self.assertEqual(results["vendor_name"], "ACME Corporation")
        self.assertEqual(results["vendor_tax_id"], "1234567890")
        self.assertEqual(results["customer_name"], "John Doe")
        self.assertEqual(results["tax_rate"], "23%")
        self.assertEqual(results["currency"], "USD")
        
        # Check extraction info
        self.assertTrue(results["extraction_info"]["invoice_number"]["success"])
        self.assertTrue(results["extraction_info"]["issue_date"]["success"])
        
        # Fields that weren't extracted
        self.assertNotIn("non_existent_field", results)
    
    def test_register_pattern(self):
        """Test registering a new pattern."""
        # Register a new pattern
        self.extractor.register_pattern(
            field_name="reference_number",
            pattern=r"Ref(?:erence)?(?:\s+No)?:?\s*([A-Za-z0-9\-]+)",
            validation_type="text",
            description="Reference number"
        )
        
        # Test the new pattern
        text = "Reference No: REF-6789"
        value, info = self.extractor.extract_field(text, "reference_number")
        self.assertEqual(value, "REF-6789")
        self.assertTrue(info["success"])


if __name__ == "__main__":
    unittest.main()
