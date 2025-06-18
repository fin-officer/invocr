#!/usr/bin/env python3
"""
Simple PDF examination script to extract text and analyze content.
"""

import sys
import os
import json
import subprocess

def extract_text_with_pdftotext(pdf_path):
    """Extract text from PDF using pdftotext command line tool"""
    try:
        # Check if pdftotext is available
        subprocess.run(['which', 'pdftotext'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Extract text using pdftotext
        result = subprocess.run(
            ['pdftotext', '-layout', pdf_path, '-'],
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        print("Error: pdftotext command failed or not available")
        return None
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

def analyze_text(text):
    """Analyze extracted text to identify key invoice fields"""
    if not text:
        return {}
    
    # Print the full text for inspection
    print("\n--- FULL TEXT CONTENT ---\n")
    print(text)
    print("\n--- END OF TEXT CONTENT ---\n")
    
    # Initialize results dictionary
    results = {
        "document_type": "invoice",
        "document_number": "",
        "issue_date": "",
        "due_date": "",
        "seller": {
            "name": "",
            "address": "",
            "tax_id": ""
        },
        "buyer": {
            "name": "",
            "address": "",
            "tax_id": ""
        },
        "items": [],
        "totals": {
            "subtotal": 0.0,
            "tax_amount": 0.0,
            "total": 0.0,
            "currency": ""
        }
    }
    
    # Split text into lines for analysis
    lines = text.split('\n')
    print(f"\nFound {len(lines)} lines of text")
    
    # Look for key invoice fields
    print("\n--- FIELD DETECTION ---\n")
    
    # Look for invoice number
    for i, line in enumerate(lines):
        if "invoice" in line.lower() and "number" in line.lower():
            print(f"Potential invoice number line ({i}): {line}")
        if "faktura" in line.lower() and "nr" in line.lower():
            print(f"Potential invoice number line (Polish) ({i}): {line}")
        if "arve" in line.lower() and "nr" in line.lower():
            print(f"Potential invoice number line (Estonian) ({i}): {line}")
    
    # Look for dates
    for i, line in enumerate(lines):
        if any(date_term in line.lower() for date_term in ["date", "kuupäev", "data"]):
            print(f"Potential date line ({i}): {line}")
    
    # Look for company names
    for i, line in enumerate(lines):
        if any(term in line.lower() for term in ["ltd", "llc", "inc", "gmbh", "ou", "sp. z o.o."]):
            print(f"Potential company name ({i}): {line}")
    
    # Look for tax IDs
    for i, line in enumerate(lines):
        if any(tax_term in line.lower() for tax_term in ["vat", "tax", "nip", "kmkr", "reg"]):
            print(f"Potential tax ID line ({i}): {line}")
    
    # Look for amounts and currency
    for i, line in enumerate(lines):
        if any(currency in line for currency in ["$", "€", "£", "PLN", "EUR", "USD"]):
            print(f"Potential amount line ({i}): {line}")
    
    # Look for item table headers
    for i, line in enumerate(lines):
        if any(all(term in line.lower() for term in pair) for pair in [
            ("item", "description"), 
            ("quantity", "price"),
            ("opis", "cena"),
            ("toode", "hind")
        ]):
            print(f"Potential item table header ({i}): {line}")
    
    return results

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_file_path> [output_json_path]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Examining PDF: {pdf_path}")
    
    # Extract text from PDF
    text = extract_text_with_pdftotext(pdf_path)
    
    if not text:
        print("Failed to extract text from PDF")
        sys.exit(1)
    
    # Analyze the extracted text
    results = analyze_text(text)
    
    # Save results if output path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {output_path}")

if __name__ == "__main__":
    main()
