#!/usr/bin/env python3
import os
import logging
from pdf2json import process_pdf_to_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pdf_processing.log')
    ]
)
logger = logging.getLogger(__name__)

def is_valid_pdf(pdf_path: str) -> bool:
    """Check if a PDF file is valid and can be read."""
    try:
        with open(pdf_path, 'rb') as f:
            # Check if file starts with PDF header
            if f.read(4) != b'%PDF':
                return False

        return True
    except Exception as e:
        logger.error(f"Error validating PDF {pdf_path}: {e}")
        return False


def process_file(pdf_path: str, output_dir: str) -> bool:
    """Process a single PDF file and save its content as JSON."""
    try:
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Validate PDF
        if not is_valid_pdf(pdf_path):
            logger.error(f"Invalid or corrupted PDF: {pdf_path}")
            return False
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save as JSON
        output_path = os.path.join(
            output_dir, 
            f"{os.path.splitext(os.path.basename(pdf_path))[0]}.json"
        )
        
        process_pdf_to_json(pdf_path, output_path)

        logger.info(f"Successfully processed: {pdf_path} -> {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}")
        return False

def process_directory(input_dir: str, output_dir: str) -> None:
    """Process all PDF files in the input directory."""
    if not os.path.isdir(input_dir):
        logger.error(f"Input directory does not exist: {input_dir}")
        return
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each PDF file
    success_count = 0
    failure_count = 0
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                print(f"Processing PDF: {pdf_path}")
                if process_file(pdf_path, output_dir):
                    success_count += 1
                else:
                    failure_count += 1
    
    logger.info(f"\nProcessing complete!")
    logger.info(f"Successfully processed: {success_count} files")
    if failure_count > 0:
        logger.warning(f"Failed to process: {failure_count} files (check logs for details)")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Process PDF files and convert them to JSON')
    parser.add_argument('--input-dir', default='2024.09/attachments', 
                       help='Directory containing PDF files (default: 2024.09/attachments)')
    parser.add_argument('--output-dir', default='2024.09/json',
                       help='Directory to save JSON files (default: 2024.09/json)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Set the logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Set log level
    logger.setLevel(args.log_level)
    
    # Process the directory
    process_directory(args.input_dir, args.output_dir)
