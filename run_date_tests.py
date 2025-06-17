#!/usr/bin/env python3
"""
Simple test runner for date extraction functionality.
This can be run independently of the main test suite.
"""
import sys
import unittest
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, '.')

# Import the functions we want to test
from invocr.formats.pdf.extractor import parse_date, extract_date

class TestDateExtraction(unittest.TestCase):
    """Test cases for date extraction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.reference_date = datetime(2023, 10, 15)  # Fixed reference date for testing
    
    def test_parse_date_standard_formats(self):
        """Test parsing of standard date formats."""
        test_cases = [
            # DD/MM/YYYY and variants
            ("15/10/2023", "2023-10-15"),
            ("15-10-2023", "2023-10-15"),
            ("15.10.2023", "2023-10-15"),
            ("15/10/23", "2023-10-15"),  # 2-digit year
            
            # MM/DD/YYYY and variants (US format)
            ("10/15/2023", "2023-10-15"),
            ("10-15-2023", "2023-10-15"),
            ("10.15.2023", "2023-10-15"),
            ("10/15/23", "2023-10-15"),  # 2-digit year
            
            # YYYY-MM-DD (ISO format)
            ("2023-10-15", "2023-10-15"),
            ("2023/10/15", "2023-10-15"),
            ("2023.10.15", "2023-10-15"),
            ("23-10-15", "2023-10-15"),  # 2-digit year ISO
            
            # Textual months
            ("15 Oct 2023", "2023-10-15"),
            ("15 October 2023", "2023-10-15"),
            ("Oct 15, 2023", "2023-10-15"),
            ("October 15, 2023", "2023-10-15"),
            ("15-Oct-2023", "2023-10-15"),
            ("15-October-2023", "2023-10-15"),
            
            # Special formats
            ("15102023", "2023-10-15"),  # DDMMYYYY
            ("20231015", "2023-10-15"),  # YYYYMMDD
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                self.assertEqual(parse_date(date_str), expected)
    
    def test_parse_date_2digit_year(self):
        """Test handling of 2-digit years."""
        current_year = datetime.now().year
        century = (current_year // 100) * 100
        
        # Test recent years (should be in current century)
        test_year = current_year % 100
        expected = f"20{test_year:02d}-10-15"
        self.assertEqual(parse_date(f"15/10/{test_year}"), expected)
        
        # Test years in the past (should be in previous century)
        past_year = 99  # 1999
        self.assertEqual(parse_date(f"15/10/{past_year}"), f"19{past_year}-10-15")
    
    def test_parse_date_relative(self):
        """Test parsing of relative dates."""
        # Test with reference date
        ref_date = datetime(2023, 10, 15)
        
        # Test relative days
        self.assertEqual(
            parse_date("30", reference_date=ref_date, is_relative=True),
            (ref_date + timedelta(days=30)).strftime("%Y-%m-%d")
        )
    
    def test_extract_date_issue_date(self):
        """Test extraction of issue dates from text."""
        test_cases = [
            ("Invoice Date: 15/10/2023", "2023-10-15"),
            ("Date: 2023-10-15", "2023-10-15"),
            ("Issued on: October 15, 2023", "2023-10-15"),
            ("Document Date: 15-Oct-2023", "2023-10-15"),
            ("Date 15102023", "2023-10-15"),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                self.assertEqual(extract_date(text, "issue"), expected)
    
    def test_extract_due_date_absolute(self):
        """Test extraction of absolute due dates."""
        test_cases = [
            ("Due Date: 15/11/2023", "2023-11-15"),
            ("Payment Due: 2023-11-15", "2023-11-15"),
            ("Due on: November 15, 2023", "2023-11-15"),
            ("Payment Due Date: 15-Nov-2023", "2023-11-15"),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                self.assertEqual(extract_date(text, "due"), expected)
    
    def test_extract_due_date_relative(self):
        """Test extraction of relative due dates."""
        # Test with explicit issue date in the text
        text = """
        Invoice Date: 2023-10-15
        Payment Terms: Net 30 days
        """
        self.assertEqual(extract_date(text, "due"), "2023-11-14")  # 30 days after Oct 15
        
        # Test with different relative formats
        test_cases = [
            ("Due in 30 days", "2023-11-14"),
            ("Payment due in 30 days", "2023-11-14"),
            ("Net 30", "2023-11-14"),
            ("Terms: 30 days net", "2023-11-14"),
        ]
        
        # Add issue date to each test case
        issue_date = "\nInvoice Date: 2023-10-15\n"
        for text, expected in test_cases:
            with self.subTest(text=text):
                self.assertEqual(extract_date(issue_date + text, "due"), expected)
    
    def test_extract_due_date_without_issue_date(self):
        """Test due date extraction when no issue date is available."""
        # Should return empty string since we can't calculate relative dates
        self.assertEqual(extract_date("Net 30 days", "due"), "")
        
        # Should still work with absolute dates
        self.assertEqual(
            extract_date("Due Date: 2023-11-15", "due"),
            "2023-11-15"
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
