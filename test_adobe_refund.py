#!/usr/bin/env python
"""
Test script for Adobe Invoice Extractor with refund handling.
This script tests the enhanced extractor's ability to handle negative values and refunds.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from invocr.extractors.specialized.adobe_extractor import AdobeInvoiceExtractor

def test_refund_parsing():
    """Test the extractor's ability to parse refund amounts."""
    print("Testing Adobe Invoice Extractor refund handling...")
    
    # Sample text with refund notation (parentheses for negative values)
    sample_refund_text = """
    Adobe Systems Software Ireland Ltd
    Invoice Number INV12345
    Invoice Date 15-JAN-2023
    Currency USD
    
    Bill To
    ACME Corporation
    123 Main St
    Anytown, USA
    
    Customer VAT No: US123456789
    
    Item Details
    Service Term: 15-JAN-2023 to 14-FEB-2023
    
    PRODUCT NUMBER  PRODUCT DESCRIPTION       QTY  EA  UNIT PRICE  NET AMOUNT  TAX RATE  TAX AMOUNT  TOTAL AMOUNT
    65304749       Adobe Creative Cloud       1    EA  (21.84)     (21.84)     0.0%      (0.00)      (21.84)
    
    Invoice Total
    NET AMOUNT (USD)  (21.84)
    TAXES (SEE DETAILS FOR RATES) (USD)  (0.00)
    GRAND TOTAL (USD)  (21.84)
    """
    
    # Create extractor with sample text
    extractor = AdobeInvoiceExtractor(ocr_text=sample_refund_text)
    
    # Extract invoice data
    invoice_data = extractor.extract_invoice_data(sample_refund_text)
    
    # Print results
    print("\nExtracted Invoice Data:")
    print(f"Invoice Number: {invoice_data.get('invoice_number', 'Not found')}")
    print(f"Issue Date: {invoice_data.get('issue_date', 'Not found')}")
    print(f"Currency: {invoice_data.get('currency', 'Not found')}")
    
    # Print items
    items = invoice_data.get('items', [])
    print(f"\nItems ({len(items)}):")
    for i, item in enumerate(items, 1):
        print(f"  Item {i}:")
        print(f"    Description: {item.get('description', 'Not found')}")
        print(f"    Quantity: {item.get('quantity', 'Not found')}")
        print(f"    Unit Price: {item.get('unit_price', 'Not found')}")
        print(f"    Net Amount: {item.get('net_amount', 'Not found')}")
        print(f"    Total: {item.get('total', 'Not found')}")
    
    # Print totals
    totals = invoice_data.get('totals', {})
    print("\nTotals:")
    print(f"  Subtotal: {totals.get('subtotal', 'Not found')}")
    print(f"  Tax Amount: {totals.get('tax_amount', 'Not found')}")
    print(f"  Total: {totals.get('total', 'Not found')}")
    
    # Verify refund amounts are negative
    items_correct = all(item.get('net_amount', 0) < 0 for item in items if 'Creative Cloud' in item.get('description', ''))
    totals_correct = totals.get('subtotal', 0) < 0 and totals.get('total', 0) < 0
    
    if items_correct and totals_correct:
        print("\n✅ SUCCESS: Refund amounts correctly extracted as negative values")
    else:
        print("\n❌ FAILURE: Refund amounts not correctly extracted as negative values")
        if not items_correct:
            print("  - Item amounts should be negative")
        if not totals_correct:
            print("  - Total amounts should be negative")

if __name__ == "__main__":
    test_refund_parsing()
