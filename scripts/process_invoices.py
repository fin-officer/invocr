#!/usr/bin/env python3
"""
Command-line interface for processing invoice PDFs using the InvOCR library.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from invocr.core import PDFProcessor


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('invoice_processing.log')
        ]
    )


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Process invoice PDFs and extract data')
    parser.add_argument(
        '--input-dir', 
        required=True,
        help='Directory containing PDF invoices'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory to save processed JSON files'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Process the directory
    processor = PDFProcessor()
    results = processor.process_directory(args.input_dir, args.output_dir)
    
    # Print summary
    print("\n=== Processing Summary ===")
    print(f"Total files processed: {results['processed']}")
    print(f"Successfully processed: {results['succeeded']}")
    print(f"Failed: {results['failed']}")
    
    if results['failed'] > 0:
        print("\nErrors encountered:")
        for error in results['errors']:
            print(f"- {error}")
    
    sys.exit(0 if results['success'] else 1)


if __name__ == "__main__":
    main()
