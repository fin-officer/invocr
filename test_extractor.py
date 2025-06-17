"""
Test script for the rule-based PDF extractor.
"""
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80 + "\n")

def test_rule_based_extractor():
    """Test the rule-based extractor with sample invoice text."""
    from invocr.formats.pdf.rule_based_extractor import RuleBasedExtractor
    from invocr.formats.pdf.models import Invoice, ContactInfo as Party, Address, InvoiceItem, PaymentInfo as PaymentTerms
    
    print_header("Testing Rule-Based Extractor")
    
    # Create extractor
    extractor = RuleBasedExtractor()
    
    # Sample invoice text
    text = """
    INVOICE #INV-2023-001
    Date: 2023-10-15
    Due Date: 2023-11-14
    
    From: Test Company Inc.
    123 Business St, City, Country
    VAT: GB123456789
    
    Bill To: Client Name
    456 Client Ave, Client City
    
    Description            Qty  Unit Price  Amount
    -----------------------------------------------
    Web Design Service     10    100.00      1000.00
    Hosting (1 year)       1     120.00      120.00
    
    Subtotal: 1120.00
    VAT (20%): 224.00
    Total: 1344.00
    
    Payment Terms: Net 30
    """
    
    print("Extracting invoice data...")
    try:
        # First try with the extract method (returns ExtractionResult)
        result = extractor.extract(text)
        if result.is_valid():
            invoice = result.data
            print("\nExtraction successful using extract() method")
        else:
            # Fall back to extract_invoice if extract fails
            print("Extract method returned invalid result, trying extract_invoice...")
            invoice = extractor.extract_invoice(text)
            print("\nExtraction successful using extract_invoice() method")
        
        # Print results
        print("\nExtraction Results:")
        print("-" * 50)
        print(f"Document Number: {getattr(invoice, 'document_number', 'N/A')}")
        print(f"Document Type: {getattr(invoice, 'document_type', 'invoice')}")
        print(f"Issue Date: {getattr(invoice, 'issue_date', 'N/A')}")
        print(f"Due Date: {getattr(invoice, 'due_date', 'N/A')}")
        
        # Seller information
        seller = getattr(invoice, 'seller', None)
        if seller:
            print("\nSeller:")
            print(f"  Name: {getattr(seller, 'name', 'N/A')}")
            print(f"  Email: {getattr(seller, 'email', 'N/A')}")
            print(f"  Phone: {getattr(seller, 'phone', 'N/A')}")
            
            seller_address = getattr(seller, 'address', None)
            if seller_address:
                print(f"  Address: {', '.join(filter(None, [
                    getattr(seller_address, 'street', ''),
                    getattr(seller_address, 'city', ''),
                    getattr(seller_address, 'state', ''),
                    getattr(seller_address, 'postal_code', ''),
                    getattr(seller_address, 'country', '')
                ])) or 'N/A'}")
        
        # Buyer information
        buyer = getattr(invoice, 'buyer', None)
        if buyer:
            print("\nBuyer:")
            print(f"  Name: {getattr(buyer, 'name', 'N/A')}")
            print(f"  Email: {getattr(buyer, 'email', 'N/A')}")
            print(f"  Phone: {getattr(buyer, 'phone', 'N/A')}")
            
            buyer_address = getattr(buyer, 'address', None)
            if buyer_address:
                print(f"  Address: {', '.join(filter(None, [
                    getattr(buyer_address, 'street', ''),
                    getattr(buyer_address, 'city', ''),
                    getattr(buyer_address, 'state', ''),
                    getattr(buyer_address, 'postal_code', ''),
                    getattr(buyer_address, 'country', '')
                ])) or 'N/A'}")
        
        # Items
        items = getattr(invoice, 'items', [])
        if items:
            print("\nItems:")
            for i, item in enumerate(items, 1):
                print(f"  {i}. {getattr(item, 'description', 'N/A')}")
                print(f"     Quantity: {getattr(item, 'quantity', 1)}")
                print(f"     Unit Price: {getattr(item, 'unit_price', 0)}")
                print(f"     Total: {getattr(item, 'total', 0)}")
                if hasattr(item, 'tax_rate') and getattr(item, 'tax_rate', 0):
                    print(f"     Tax Rate: {getattr(item, 'tax_rate', 0)}%")
        
        # Totals
        totals = getattr(invoice, 'totals', None)
        if totals:
            print("\nTotals:")
            print(f"  Subtotal: {getattr(totals, 'subtotal', 'N/A')}")
            if hasattr(totals, 'tax_rate') and getattr(totals, 'tax_rate', 0):
                print(f"  Tax ({getattr(totals, 'tax_rate', 0)}%): {getattr(totals, 'tax_amount', 'N/A')}")
            if hasattr(totals, 'shipping') and getattr(totals, 'shipping', 0):
                print(f"  Shipping: {getattr(totals, 'shipping', 'N/A')}")
            if hasattr(totals, 'discount') and getattr(totals, 'discount', 0):
                print(f"  Discount: {getattr(totals, 'discount', 'N/A')}")
            print(f"  Total: {getattr(totals, 'total', 'N/A')} {getattr(invoice, 'currency', '')}")
        
        # Payment information
        payment_terms = getattr(invoice, 'payment_terms', '')
        if payment_terms:
            print(f"\nPayment Terms: {payment_terms}")
            
        payment_info = getattr(invoice, 'payment_info', None)
        if payment_info:
            print("\nPayment Information:")
            if getattr(payment_info, 'account_name', None):
                print(f"  Account Name: {payment_info.account_name}")
            if getattr(payment_info, 'account_number', None):
                print(f"  Account Number: {payment_info.account_number}")
            if getattr(payment_info, 'bank_name', None):
                print(f"  Bank: {payment_info.bank_name}")
            if getattr(payment_info, 'iban', None):
                print(f"  IBAN: {payment_info.iban}")
            if getattr(payment_info, 'swift', None):
                print(f"  SWIFT/BIC: {payment_info.swift}")
        
        print("\nRaw JSON output:")
        print(json.dumps(invoice.to_dict(), indent=2, default=str) if hasattr(invoice, 'to_dict') else "No to_dict method available")
        
        print("\nTest completed successfully!")
        return True
    except Exception as e:
        print(f"\nError during extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_rule_based_extractor()
