"""
OCR Text command module.

Handles the 'ocr-text' command for extracting and viewing OCR text from documents.
"""

import sys
import click
from pathlib import Path

from invocr.utils.logger import get_logger
from invocr.utils.ocr import extract_text
from ..common import load_yaml_config

logger = get_logger(__name__)


@click.command(name='ocr-text')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-l', '--languages', help='OCR languages (e.g., en,pl,de)')
@click.option('-o', '--output-file', type=click.Path(), help='Save OCR text to file')
@click.option('--layout/--no-layout', default=True, help='Preserve layout information')
@click.option('-p', '--pages', help='Specific pages to extract (e.g., 1,2,5)')
def ocr_text_command(input_file, languages, output_file, layout, pages):
    """
    Extract and view OCR text from a document.
    
    This command extracts text from a document using OCR and displays it or saves it to a file.
    """
    try:
        # Parse languages option
        ocr_languages = ["eng", "pol", "est", "deu"]
        if languages:
            ocr_languages = languages.split(',')
            
        # Extract text
        logger.info(f"Extracting OCR text from {input_file}")
        
        # Parse pages option
        page_list = None
        if pages:
            try:
                page_list = [int(p.strip()) for p in pages.split(',')]
            except ValueError:
                logger.warning(f"Invalid page numbers: {pages}. Using all pages.")
        
        ocr_text = extract_text(input_file, languages=ocr_languages, use_layout=layout, pages=page_list)
        
        # Output text
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(ocr_text)
            logger.info(f"OCR text saved to {output_file}")
        else:
            # Print to console
            print("\n" + "=" * 80)
            print(f"OCR TEXT FROM: {input_file}")
            print("=" * 80 + "\n")
            print(ocr_text)
            print("\n" + "=" * 80)
            
        return 0
        
    except Exception as e:
        logger.error(f"Error extracting OCR text: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1
