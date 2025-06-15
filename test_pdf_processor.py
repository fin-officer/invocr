#!/usr/bin/env python3
"""
Test script for the PDFProcessor class
"""
import sys
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from invocr.formats.pdf import PDFProcessor

def test_pdf_processor(pdf_path: str):
    """Test the PDF processor with a sample invoice"""
    print(f"Testing PDF processor with: {pdf_path}")
    print("-" * 80)
    
    # Initialize the processor
    processor = PDFProcessor()
    
    # Extract text
    text = processor.extract_text(pdf_path)
    print(f"Extracted text length: {len(text)} characters")
    
    # Extract structured data
    data = processor.extract_structured_data(pdf_path)
    
    # Print the extracted data
    print("\nExtracted structured data:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Save to JSON file
    output_path = Path(pdf_path).with_suffix('.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")
    
    return data

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Default test file
        pdf_path = "tests/data/sample_invoice.pdf"
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        print("Please provide a valid PDF file path as an argument.")
        sys.exit(1)
    
    test_pdf_processor(pdf_path)
