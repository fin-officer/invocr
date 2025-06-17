#!/usr/bin/env python3
import sys
from pdf2json import extract_text_from_pdf

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_pdf.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    print(f"Extracting text from {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)
    print("\n--- EXTRACTED TEXT ---")
    print(text)
    print("--- END OF EXTRACTED TEXT ---")
