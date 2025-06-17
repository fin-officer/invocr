#!/usr/bin/env python3
"""
Example script: process_invocr.py
Usage:
    python process_invocr.py --input-dir /path/to/input --output-dir /path/to/output

This script uses the invocr library to convert PDF invoices to structured JSON.
"""
import argparse
import sys
from pathlib import Path
from invocr.core.converter import UniversalConverter

def process_pdf(input_pdf: Path, output_json: Path, converter: UniversalConverter):
    print(f"Processing PDF: {input_pdf}")
    data = converter.pdf_to_json(input_pdf)
    output_json.write_text(
        __import__('json').dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"JSON saved to {output_json}")


def main():
    parser = argparse.ArgumentParser(description="Batch process PDFs with invocr.")
    parser.add_argument("--input-dir", required=True, help="Input directory with PDF files")
    parser.add_argument("--output-dir", required=True, help="Output directory for JSON files")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = UniversalConverter(languages=["pl", "en", "de", "fr", "es"])
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    for pdf_path in pdf_files:
        output_path = output_dir / (pdf_path.stem + ".json")
        process_pdf(pdf_path, output_path, converter)
    print(f"\nProcessing complete!\nSuccessfully processed: {len(pdf_files)} files")

if __name__ == "__main__":
    main()
