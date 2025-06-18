"""
PDF to JSON command module.

Handles the 'pdf2json' command for converting PDF invoices to structured JSON.
"""

import os
import sys
import click
from pathlib import Path

from invocr.utils.logger import get_logger
from invocr.utils.ocr import extract_text
from invocr.formats.pdf.extractor import extract_invoice_data

logger = get_logger(__name__)


@click.command(name='pdf2json')
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output JSON file path')
def pdf2json_command(pdf_path, output):
    """Convert PDF invoice to structured JSON"""
    try:
        # Extract text from PDF
        logger.info(f"Extracting text from {pdf_path}...")
        text = extract_text(pdf_path)
        
        # Extract structured data from the text
        logger.info("Structuring invoice data...")
        structured_data = extract_invoice_data(text)
        
        # Determine output path if not provided
        if not output:
            output = os.path.splitext(pdf_path)[0] + '.json'
        
        # Save the JSON
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            import json
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON saved to {output}")
        
        return structured_data
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)
