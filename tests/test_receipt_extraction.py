"""
Tests for receipt extraction functionality.
"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from invocr.formats.pdf.document import (
    Address,
    Invoice,
    InvoiceItem,
    Party,
    PaymentTerms,
)
from invocr.formats.pdf.rule_based_extractor import RuleBasedExtractor


def create_receipt_extractor():
    """Create a rule-based extractor for receipt testing."""
    return RuleBasedExtractor()


def test_extract_receipt_basic():
    """Test basic receipt extraction."""
    extractor = create_receipt_extractor()

    # Sample receipt text with consistent indentation
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
    """
    
    # Print receipt text in raw format for debugging
    print("\n=== RAW RECEIPT TEXT ===\n")
    print(repr(text))
    print("\n=== END RAW RECEIPT TEXT ===\n")
    
    # Print receipt text with line numbers for debugging
    print("\n=== RECEIPT TEXT WITH LINE NUMBERS ===\n")
    for i, line in enumerate(text.split('\n'), 1):
        # Replace whitespace with visible characters to debug spacing issues
        visible_whitespace = line.replace(' ', '·')
        print(f"{i:2d}: {visible_whitespace}")
    print("\n=== END RECEIPT TEXT ===\n")
    
    # Highlight expected item section
    print("\n=== EXPECTED ITEM SECTION ===\n")
    print("GROCERIES\nApple           1.00lb  2.49    2.49\nMilk              1     3.99    3.99\nBread             1     2.50    2.50")
    print("\n=== END EXPECTED ITEM SECTION ===\n")

    # Extract invoice data
    invoice = extractor.extract_invoice(text)
    
    # Print extraction results for debugging
    print(f"\n=== EXTRACTION RESULTS ===\n")
    print(f"Invoice Number: {invoice.invoice_number}")
    print(f"Issue Date: {invoice.issue_date}")
    print(f"Currency: {invoice.currency}")
    print(f"Total: {invoice.total_amount}")
    print(f"Tax: {invoice.tax_amount}")
    
    print(f"\nExtracted {len(invoice.items)} items:")
    for i, item in enumerate(invoice.items, 1):
        print(f"  {i}. {item.description} x {item.quantity}{item.unit} @ ${item.unit_price:.2f} = ${item.total_amount:.2f}")
    print("\n=== END EXTRACTION RESULTS ===")

    # Print the receipt text with visible whitespace for debugging
    print("\n=== Test Receipt Text (with visible whitespace) ===")
    print(repr(text))
    print("=" * 80)
    
    # Print the receipt text with line numbers for debugging
    print("\n=== Receipt Text with Line Numbers ===")
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        # Highlight the item section
        highlight = ""
        if i >= 13 and i <= 16:  # Item lines in our test receipt
            highlight = "  <<< ITEM LINE"
        print(f"{i:2d}: {line!r}{highlight}")
    
    print("\n=== Item Section Analysis ===")
    print("Looking for item section between 'ITEM' and 'SUBTOTAL'...")
    
    # Manually extract what we expect to be the item section
    expected_item_section = """GROCERIES
    Apple           1.00lb  2.49    2.49
    Milk              1     3.99    3.99
    Bread             1     2.50    2.50"""
    
    print("\nExpected item section:")
    print("---")
    print(expected_item_section)
    print("---")
    
    # Extract invoice data
    print("\n=== Extracting invoice data ===")
    result = extractor.extract_invoice(text)
    
    # Print extraction results
    print("\n=== Extraction Results ===")
    if result is None:
        print("❌ Extraction returned None")
        assert False, "Extraction returned None"
    
    print(f"Extracted invoice number: {getattr(result, 'invoice_number', 'N/A')}")
    print(f"Extracted issue date: {getattr(result, 'issue_date', 'N/A')}")
    print(f"Extracted currency: {getattr(result, 'currency', 'N/A')}")
    print(f"Extracted total amount: {getattr(result, 'total_amount', 'N/A')}")
    print(f"Extracted tax amount: {getattr(result, 'tax_amount', 'N/A')}")
    
    print(f"\nExtracted items: {len(result.items) if hasattr(result, 'items') else 'N/A'}")
    if hasattr(result, 'items') and result.items:
        for i, item in enumerate(result.items, 1):
            print(f"  {i}. {item.description}: {item.quantity} {getattr(item, 'unit', '')} x {item.unit_price} = {item.total_amount}")
    else:
        print("❌ No items were extracted")

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
    assert hasattr(result, "payment_method")
    assert "credit card" in result.payment_method.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
