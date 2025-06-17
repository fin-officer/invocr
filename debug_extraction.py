#!/usr/bin/env python3
import sys
import json
import re
from pdf2json import extract_text_from_pdf

def extract_openrouter_data(text):
    """Special extraction just for OpenRouter receipts"""
    lines = text.split('\n')
    
    # Initialize data structure
    data = {
        "invoice_number": None,
        "invoice_date": None,
        "seller": {"name": None, "address": None, "tax_id": None},
        "buyer": {"name": None, "address": None, "tax_id": None},
        "items": [],
        "totals": {"net": None, "tax": None, "gross": None, "currency": "USD"}
    }
    
    # Print all lines for debugging
    print("--- LINE BY LINE ANALYSIS ---")
    for i, line in enumerate(lines):
        print(f"Line {i}: '{line}'")
    
    # Extract invoice number
    for line in lines:
        if "Invoice number" in line:
            match = re.search(r'Invoice number\s+([A-Za-z0-9-]+)', line)
            if match:
                data["invoice_number"] = match.group(1)
                print(f"Found invoice number: {data['invoice_number']}")
                break
    
    # Extract date
    for line in lines:
        if "Date paid" in line:
            match = re.search(r'Date paid\s+([A-Za-z]+ \d+, \d{4})', line)
            if match:
                data["invoice_date"] = match.group(1)
                print(f"Found date: {data['invoice_date']}")
                break
    
    # Find quantity and price
    qty_found = False
    price_found = False
    for i, line in enumerate(lines):
        if "Qty" in line and "Unit price" in line:
            print(f"Found Qty/Unit price header at line {i}")
            # Check the next line for quantity and price
            if i + 1 < len(lines):
                qty_line = lines[i + 1]
                print(f"Checking line {i+1} for qty/price: '{qty_line}'")
                match = re.search(r'(\d+)\s+\$(\d+\.\d+)', qty_line)
                if match:
                    qty = int(match.group(1))
                    price = float(match.group(2))
                    print(f"Found quantity: {qty}, price: ${price}")
                    qty_found = True
                    price_found = True
                    
                    # Add item
                    item = {
                        "description": "OpenRouter Credits",
                        "quantity": qty,
                        "unit_price": price,
                        "net_amount": qty * price,
                        "tax_rate": 0.0,
                        "tax_amount": 0.0,
                        "total": qty * price
                    }
                    data["items"].append(item)
                    data["totals"]["net"] = qty * price
                    print(f"Added item: {item}")
    
    # Find amount/total
    for i, line in enumerate(lines):
        if "Amount" in line and i + 1 < len(lines):
            amount_line = lines[i + 1]
            print(f"Checking line {i+1} for amount: '{amount_line}'")
            match = re.search(r'\$(\d+\.\d+)', amount_line)
            if match:
                amount = float(match.group(1))
                print(f"Found amount: ${amount}")
                data["totals"]["gross"] = amount
                break
    
    # If we still don't have a gross amount, look for "paid"
    if not data["totals"]["gross"]:
        for line in lines:
            if "paid" in line:
                match = re.search(r'\$(\d+\.\d+)', line)
                if match:
                    amount = float(match.group(1))
                    print(f"Found paid amount: ${amount}")
                    data["totals"]["gross"] = amount
                    break
    
    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_extraction.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    print(f"Extracting text from {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)
    
    print("\n--- EXTRACTED DATA ---")
    data = extract_openrouter_data(text)
    
    print("\n--- FINAL JSON ---")
    print(json.dumps(data, indent=2))
