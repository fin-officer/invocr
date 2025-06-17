"""
Tests for receipt extraction functionality.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, date
import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from invocr.formats.pdf.rule_based_extractor import RuleBasedExtractor
from invocr.formats.pdf.document import Invoice, Party, Address, InvoiceItem, PaymentTerms

def create_receipt_extractor():
    """Create a rule-based extractor for receipt testing."""
    return RuleBasedExtractor()

def test_extract_receipt_basic():
    """Test basic receipt extraction."""
    extractor = create_receipt_extractor()
    
    # Sample receipt text
    text = """
    ACME STORE
    123 Main Street
    Anytown, ST 12345
    (555) 123-4567
    
    Receipt #2762-0364
    Date: 11/15/2024 14:30:22
    Cashier: John D
    
    ---------------------------------
    ITEM                QTY  PRICE  TOTAL
    ---------------------------------
    GROCERIES
    Apple           1.00lb  2.49    2.49
    Milk              1     3.99    3.99
    Bread             1     2.50    2.50
    
    SUBTOTAL:               8.98
    TAX:                   0.72
    TOTAL:                9.70
    
    CASH TEND:           10.00
    CHANGE:               0.30
    
    Thank you for shopping with us!
    """
    
    # Extract invoice data
    result = extractor.extract_invoice(text)
    
    # Basic assertions
    assert result is not None
    assert isinstance(result, Invoice)
    assert result.invoice_number == "2762-0364"
    assert result.issue_date == date(2024, 11, 15)
    assert result.currency == "USD"
    assert len(result.items) == 3
    assert abs(result.total_amount - 9.70) < 0.01
    assert abs(result.tax_amount - 0.72) < 0.01
    
    # Verify items
    items = result.items
    assert items[0].description == "Apple"
    assert abs(items[0].quantity - 1.0) < 0.01
    assert abs(items[0].unit_price - 2.49) < 0.01
    
    assert items[1].description == "Milk"
    assert items[2].description == "Bread"

def test_extract_receipt_with_payment_method():
    """Test receipt extraction with payment method."""
    extractor = create_receipt_extractor()
    
    # Sample receipt text with payment method
    text = """
    RETAIL STORE
    456 Market St
    
    Receipt #2914-4703
    Date: 11/20/2024 09:15:45
    
    ITEM          QTY  PRICE  TOTAL
    -----------------------------
    Notebook      2     1.99    3.98
    Pens          3     0.99    2.97
    
    SUBTOTAL:         6.95
    TAX:               0.56
    TOTAL:            7.51
    
    Payment Method: Credit Card
    Card: **** **** **** 4242
    
    Thank you!
    """
    
    # Extract invoice data
    result = extractor.extract_invoice(text)
    
    # Verify extraction
    assert result is not None
    assert result.invoice_number == "2914-4703"
    assert len(result.items) == 2
    assert abs(result.total_amount - 7.51) < 0.01
    
    # Payment method should be extracted as metadata
    assert hasattr(result, 'payment_method')
    assert 'credit card' in result.payment_method.lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
