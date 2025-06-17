"""
Test script for PDF extractor functionality
"""

import json
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_extract_from_pdf():
    """Test extracting data from a sample PDF"""
    # Import the extractor module
    from invocr.formats.pdf.extractor import (
        extract_date,
        extract_document_number,
        extract_items,
        extract_notes,
        extract_party,
        extract_payment_terms,
        extract_totals,
    )

    # Path to sample PDF
    sample_pdf = project_root / "tests" / "data" / "sample_invoice.pdf"

    # Check if the sample PDF exists
    if not sample_pdf.exists():
        print(f"Error: Sample PDF not found at {sample_pdf}")
        return False

    print(f"Testing extraction from: {sample_pdf}")

    # Read the PDF text (in a real scenario, use pdf_to_text from converter.py)
    try:
        # For now, we'll just test the functions with sample text
        # In a real test, you would extract text from the PDF first
        sample_text = """
        INVOICE #INV-2023-001
        Date: 2023-10-15
        Due Date: 2023-11-14
        
        From: Test Company Inc.
        123 Business St, City, Country
        VAT: GB123456789
        
        Bill To: Client Name
        456 Client Ave, Client City
        
        Description           Qty  Unit Price  Total
        ----------------------------------------------
        Web Design Service    1     1000.00    1000.00
        Hosting (1 year)      1     120.00     120.00
        
        Subtotal: 1120.00
        VAT (20%): 224.00
        Total: 1344.00
        
        Payment Terms: Net 30 days
        Bank: Test Bank
        IBAN: GB29 NWBK 6016 1331 9268 19
        
        Thank you for your business!
        """

        # Test document number extraction
        doc_number = extract_document_number(sample_text)
        print(f"Extracted document number: {doc_number}")

        # Test date extraction
        issue_date = extract_date(sample_text)
        print(f"Extracted issue date: {issue_date}")

        # Test party extraction
        seller = extract_party(sample_text, "seller")
        print(f"Extracted seller: {json.dumps(seller, indent=2)}")

        buyer = extract_party(sample_text, "buyer")
        print(f"Extracted buyer: {json.dumps(buyer, indent=2)}")

        # Test items extraction
        items = extract_items(sample_text)
        print(f"Extracted items: {json.dumps(items, indent=2)}")

        # Test totals extraction
        totals = extract_totals(sample_text)
        print(f"Extracted totals: {json.dumps(totals, indent=2)}")

        # Test payment terms extraction
        payment_terms = extract_payment_terms(sample_text)
        print(f"Extracted payment terms: {payment_terms}")

        # Test notes extraction
        notes = extract_notes(sample_text)
        print(f"Extracted notes: {notes}")

        return True

    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Starting PDF extractor test...")
    success = test_extract_from_pdf()
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
