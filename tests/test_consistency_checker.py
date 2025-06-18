"""
Unit tests for the consistency checker module.

This module contains tests for the context-aware cross-field consistency
checker to ensure it correctly validates relationships between invoice fields.
"""

import unittest
from decimal import Decimal
from datetime import datetime, timedelta

from invocr.formats.pdf.extractors.specialized.consistency_checker import ConsistencyChecker


class TestConsistencyChecker(unittest.TestCase):
    """Test cases for the ConsistencyChecker class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.checker = ConsistencyChecker(tolerance=0.01)
        
        # Sample invoice data for testing
        self.sample_data = {
            "invoice_number": "INV-12345",
            "issue_date": "2023-01-15",
            "due_date": "2023-02-15",
            "currency": "USD",
            "total_amount": "$1,234.56",
            "subtotal": "$1,124.56",
            "tax_amount": "$110.00",
            "tax_rate": "9.8%",
            "items": [
                {
                    "description": "Item 1",
                    "quantity": 2,
                    "unit_price": "$500.00",
                    "amount": "$1,000.00"
                },
                {
                    "description": "Item 2",
                    "quantity": 1,
                    "unit_price": "$124.56",
                    "amount": "$124.56"
                }
            ]
        }
    
    def test_parse_amount(self):
        """Test parsing of amount values."""
        # Test various formats
        self.assertEqual(self.checker._parse_amount("$1,234.56"), Decimal("1234.56"))
        self.assertEqual(self.checker._parse_amount("€1.234,56"), Decimal("1234.56"))
        self.assertEqual(self.checker._parse_amount("1234.56"), Decimal("1234.56"))
        self.assertEqual(self.checker._parse_amount(1234.56), Decimal("1234.56"))
        self.assertEqual(self.checker._parse_amount(Decimal("1234.56")), Decimal("1234.56"))
        
        # Test invalid values
        self.assertIsNone(self.checker._parse_amount("invalid"))
        self.assertIsNone(self.checker._parse_amount(None))
    
    def test_parse_date(self):
        """Test parsing of date values."""
        # Test various formats
        self.assertEqual(self.checker._parse_date("2023-01-15"), datetime(2023, 1, 15))
        self.assertEqual(self.checker._parse_date("15-01-2023"), datetime(2023, 1, 15))
        self.assertEqual(self.checker._parse_date("01/15/2023"), datetime(2023, 1, 15))
        self.assertEqual(self.checker._parse_date("15.01.2023"), datetime(2023, 1, 15))
        self.assertEqual(self.checker._parse_date("Jan 15 2023"), datetime(2023, 1, 15))
        
        # Test datetime object
        dt = datetime(2023, 1, 15)
        self.assertEqual(self.checker._parse_date(dt), dt)
        
        # Test invalid values
        self.assertIsNone(self.checker._parse_date("invalid"))
        self.assertIsNone(self.checker._parse_date(None))
    
    def test_are_amounts_equal(self):
        """Test amount equality checking with tolerance."""
        # Test exact equality
        self.assertTrue(self.checker._are_amounts_equal("$100.00", "$100.00"))
        self.assertTrue(self.checker._are_amounts_equal(100, 100.00))
        
        # Test within tolerance
        self.assertTrue(self.checker._are_amounts_equal("$100.00", "$100.99"))  # Within 1% tolerance
        self.assertTrue(self.checker._are_amounts_equal(100, 100.99))
        
        # Test outside tolerance
        self.assertFalse(self.checker._are_amounts_equal("$100.00", "$102.00"))  # Outside 1% tolerance
        self.assertFalse(self.checker._are_amounts_equal(100, 102))
        
        # Test with invalid values
        self.assertFalse(self.checker._are_amounts_equal("invalid", "$100.00"))
        self.assertFalse(self.checker._are_amounts_equal(None, 100))
    
    def test_check_total_consistency(self):
        """Test total amount consistency check."""
        # Test valid data
        result = self.checker.check_total_consistency(self.sample_data)
        self.assertTrue(result["valid"])
        
        # Test invalid data - inconsistent total
        invalid_data = self.sample_data.copy()
        invalid_data["total_amount"] = "$1,300.00"
        result = self.checker.check_total_consistency(invalid_data)
        self.assertFalse(result["valid"])
        
        # Test missing data
        missing_data = self.sample_data.copy()
        del missing_data["total_amount"]
        result = self.checker.check_total_consistency(missing_data)
        self.assertFalse(result["valid"])
        
        # Test with missing tax (should assume 0)
        no_tax_data = self.sample_data.copy()
        no_tax_data["total_amount"] = "$1,124.56"
        del no_tax_data["tax_amount"]
        result = self.checker.check_total_consistency(no_tax_data)
        self.assertTrue(result["valid"])
    
    def test_check_line_items_sum(self):
        """Test line items sum consistency check."""
        # Test valid data
        result = self.checker.check_line_items_sum(self.sample_data)
        self.assertTrue(result["valid"])
        
        # Test invalid data - inconsistent item sum
        invalid_data = self.sample_data.copy()
        invalid_data["items"][0]["amount"] = "$900.00"
        result = self.checker.check_line_items_sum(invalid_data)
        self.assertFalse(result["valid"])
        
        # Test missing data
        missing_data = self.sample_data.copy()
        del missing_data["items"]
        result = self.checker.check_line_items_sum(missing_data)
        self.assertFalse(result["valid"])
    
    def test_check_date_consistency(self):
        """Test date consistency check."""
        # Test valid data
        result = self.checker.check_date_consistency(self.sample_data)
        self.assertTrue(result["valid"])
        
        # Test invalid data - issue date after due date
        invalid_data = self.sample_data.copy()
        invalid_data["issue_date"] = "2023-03-15"
        result = self.checker.check_date_consistency(invalid_data)
        self.assertFalse(result["valid"])
        
        # Test invalid data - due date too far in future
        far_future_data = self.sample_data.copy()
        far_future_data["due_date"] = "2025-01-15"
        result = self.checker.check_date_consistency(far_future_data)
        self.assertFalse(result["valid"])
        
        # Test missing data
        missing_data = self.sample_data.copy()
        del missing_data["due_date"]
        result = self.checker.check_date_consistency(missing_data)
        self.assertTrue(result["valid"])  # Should pass if data is missing
    
    def test_check_currency_consistency(self):
        """Test currency consistency check."""
        # Test valid data
        result = self.checker.check_currency_consistency(self.sample_data)
        self.assertTrue(result["valid"])
        
        # Test invalid data - inconsistent currency
        invalid_data = self.sample_data.copy()
        invalid_data["total_amount"] = "€1,234.56"
        result = self.checker.check_currency_consistency(invalid_data)
        self.assertFalse(result["valid"])
        
        # Test missing currency
        missing_data = self.sample_data.copy()
        del missing_data["currency"]
        result = self.checker.check_currency_consistency(missing_data)
        self.assertTrue(result["valid"])  # Should pass if currency is not specified
    
    def test_check_tax_calculation(self):
        """Test tax calculation consistency check."""
        # Test valid data
        result = self.checker.check_tax_calculation(self.sample_data)
        self.assertTrue(result["valid"])
        
        # Test invalid data - inconsistent tax calculation
        invalid_data = self.sample_data.copy()
        invalid_data["tax_amount"] = "$150.00"
        result = self.checker.check_tax_calculation(invalid_data)
        self.assertFalse(result["valid"])
        
        # Test missing tax rate but reasonable tax amount
        no_rate_data = self.sample_data.copy()
        del no_rate_data["tax_rate"]
        result = self.checker.check_tax_calculation(no_rate_data)
        self.assertTrue(result["valid"])
        
        # Test unreasonably high tax without rate
        high_tax_data = self.sample_data.copy()
        high_tax_data["tax_amount"] = "$500.00"
        del high_tax_data["tax_rate"]
        result = self.checker.check_tax_calculation(high_tax_data)
        self.assertFalse(result["valid"])
    
    def test_check_all(self):
        """Test running all consistency checks."""
        # Test valid data
        result = self.checker.check_all(self.sample_data)
        self.assertTrue(result["overall_valid"])
        self.assertEqual(len(result["checks"]), 5)  # Should have 5 checks
        
        # Test invalid data
        invalid_data = self.sample_data.copy()
        invalid_data["total_amount"] = "$1,500.00"  # Inconsistent total
        invalid_data["issue_date"] = "2023-03-15"   # Date inconsistency
        
        result = self.checker.check_all(invalid_data)
        self.assertFalse(result["overall_valid"])
        self.assertFalse(result["checks"]["total_consistency"]["valid"])
        self.assertFalse(result["checks"]["date_consistency"]["valid"])


if __name__ == "__main__":
    unittest.main()
