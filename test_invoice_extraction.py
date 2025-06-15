#!/usr/bin/env python3
"""
Test script for invoice extraction
"""
import json
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from invocr.core.extractor import DataExtractor
from invocr.formats.pdf import PDFProcessor

def extract_invoice_data(pdf_path: str) -> dict:
    """Extract data from an invoice PDF"""
    # Initialize processors
    pdf_processor = PDFProcessor()
    extractor = DataExtractor(languages=["en"])
    
    # Extract text from PDF
    text = pdf_processor.extract_text(pdf_path)
    if not text:
        raise ValueError("Failed to extract text from PDF")
    
    # Extract structured data
    data = extractor.extract_invoice_data(text, document_type="invoice")
    return data

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    try:
        result = extract_invoice_data(pdf_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
