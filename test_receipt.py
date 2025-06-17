"""
Test receipt extraction directly without pytest.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from invocr.formats.pdf.rule_based_extractor import RuleBasedExtractor

def test_receipt_extraction():
    """Test receipt extraction with a sample receipt."""
    print("Testing receipt extraction...")
    
    # Import the extractor and get default rules
    from invocr.formats.pdf.config import get_default_rules
    
    # Get the rules (already properly structured with 'fields' key)
    rules = get_default_rules()
    
    # Debug: Print the structure of the rules
    print("\nRule Structure:")
    print(f"Top-level keys: {list(rules.keys())}")
    if 'fields' in rules:
        print(f"Field rules: {list(rules['fields'].keys())}")
    
    # Create extractor with the rules
    print("\nInitializing RuleBasedExtractor...")
    extractor = RuleBasedExtractor(rules=rules)
    
    # Debug: Print the compiled patterns
    if hasattr(extractor, '_compiled_patterns'):
        print("\nCompiled Patterns:")
        for field, patterns in extractor._compiled_patterns.items():
            print(f"- {field}: {len(patterns)} patterns")
    
    # Sample receipt text
    receipt_text = """
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
    
    print("\nExtracting data from receipt...")
    try:
        result = extractor.extract_invoice(receipt_text)
        print("Extraction completed successfully")
    except Exception as e:
        print(f"Error during extraction: {e}")
        raise
    
    print("\nExtraction Results:")
    print("-" * 50)
    print(f"Receipt Number: {getattr(result, 'invoice_number', 'Not found')}")
    print(f"Date: {getattr(result, 'issue_date', 'Not found')}")
    print(f"Total Amount: {getattr(result, 'total_amount', 'Not found')}")
    print(f"Tax Amount: {getattr(result, 'tax_amount', 'Not found')}")
    
    if hasattr(result, 'items') and result.items:
        print("\nItems:")
        for i, item in enumerate(result.items, 1):
            print(f"  {i}. {item.description}: {item.quantity} x {item.unit_price} = {item.amount}")
    else:
        print("\nNo items found in the receipt.")

if __name__ == "__main__":
    test_receipt_extraction()
