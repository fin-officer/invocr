"""Debug script for receipt item extraction."""
import re

def test_receipt_patterns():
    """Test different regex patterns for extracting receipt items."""
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

    print("=== Testing receipt patterns ===\n")
    
    # Pattern 1: Match between ITEM header and SUBTOTAL
    pattern1 = r'(?s)ITEM.*?TOTAL\s*-+\s*(.*?)\s*SUBTOTAL'
    match1 = re.search(pattern1, text, re.IGNORECASE)
    print("Pattern 1 (ITEM to SUBTOTAL):")
    if match1:
        print("✅ Match found!")
        print("Captured group:\n---\n{}\\n---\n".format(match1.group(1)))
    else:
        print("❌ No match")
    
    # Pattern 2: Match GROCERIES section
    pattern2 = r'(?s)GROCERIES\s*\n(.*?)\n\s*\n'
    match2 = re.search(pattern2, text, re.IGNORECASE)
    print("\nPattern 2 (GROCERIES section):")
    if match2:
        print("✅ Match found!")
        print("Captured group:\n---\n{}\\n---\n".format(match2.group(1)))
    else:
        print("❌ No match")
    
    # Pattern 3: Match individual item lines
    print("\nPattern 3 (Individual items):")
    item_pattern = r'^\s*([A-Za-z]+)\s+([\d.]+(?:lb)?)\s+([\d.]+)\s+([\d.]+)\s*$'
    for line in text.split('\n'):
        if re.match(item_pattern, line.strip()):
            print(f"✅ Item line: {line.strip()}")
            match = re.match(item_pattern, line.strip())
            print(f"   - Description: {match.group(1).strip()}")
            print(f"   - Quantity: {match.group(2).strip()}")
            print(f"   - Price: {match.group(3).strip()}")
            print(f"   - Total: {match.group(4).strip()}")
    
    # Pattern 4: Match between dashes
    pattern4 = r'(?s)-{5,}\s*\n(.*?)\n\s*-{5,}'
    match4 = re.search(pattern4, text)
    print("\nPattern 4 (Between dashes):")
    if match4:
        print("✅ Match found!")
        print("Captured group:\n---\n{}\\n---\n".format(match4.group(1)))
    else:
        print("❌ No match")

if __name__ == "__main__":
    test_receipt_patterns()
