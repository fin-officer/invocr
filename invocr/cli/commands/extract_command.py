"""
Extract command module.

Handles the 'extract' command for extracting data from documents.
"""

import os
import sys
import json
import logging
import click
from pathlib import Path
from typing import List, Dict, Any

# Używamy adapterów zamiast bezpośrednich importów
from invocr.adapters.utils_adapter import get_logger
from invocr.adapters.extraction_adapter import ExtractionWorkflow, process_document, batch_process
from ..common import load_yaml_config

logger = get_logger(__name__)


@click.command(name='extract')
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('-c', '--config', 'config_file', type=click.Path(exists=True),
              help='Path to YAML configuration file')
@click.option('-b', '--batch', is_flag=True, help='Process input as directory of files')
@click.option('-l', '--languages', help='OCR languages (e.g., eng,pol,deu)')
@click.option('-s', '--save-ocr', is_flag=True, help='Save OCR text to file')
@click.option('-t', '--tolerance', type=float, default=0.01, 
              help='Tolerance for numerical consistency checks (default: 0.01)')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
def extract_command(input_file, output_file, config_file, batch, languages, save_ocr, tolerance, verbose):
    """Extract data from document to structured format with validation and consistency checks"""
    try:
        # Set up logging
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        # Load configuration if provided
        config = None
        if config_file:
            config = load_yaml_config(config_file)
            
            # Use config values if command-line options not provided
            if not languages and 'extraction' in config and 'languages' in config['extraction']:
                languages = ','.join(config['extraction']['languages'])
            
            if 'extraction' in config and 'tolerance' in config['extraction'] and tolerance == 0.01:
                tolerance = config['extraction']['tolerance']
        
        # Parse languages
        lang_list = None
        if languages:
            lang_list = [lang.strip() for lang in languages.split(',')]
        else:
            lang_list = ["eng"]  # Default to English
        
        logger.info(f"Using OCR languages: {', '.join(lang_list)}")
        
        # Process in batch mode if specified
        if batch:
            if not os.path.isdir(input_file):
                logger.error(f"Batch mode requires input to be a directory: {input_file}")
                sys.exit(1)
                
            # Create output directory if it doesn't exist
            os.makedirs(output_file, exist_ok=True)
            
            # Find all PDF files in the input directory
            pdf_files = []
            for root, _, files in os.walk(input_file):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
            
            if not pdf_files:
                logger.error(f"No PDF files found in {input_file}")
                sys.exit(1)
                
            logger.info(f"Found {len(pdf_files)} PDF files to process")
            
            # Process all files in batch
            results = batch_process_invoices(
                file_paths=pdf_files,
                output_dir=output_file,
                ocr_languages=lang_list,
                debug=verbose
            )
            
            # Write summary report
            summary = {
                "total": len(results),
                "successful": sum(1 for r in results if r.get("success", False)),
                "failed": sum(1 for r in results if not r.get("success", False)),
                "files": [{"file": r["file_path"], "success": r["success"]} for r in results]
            }
            
            summary_path = os.path.join(output_file, "extraction_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
                
            logger.info(f"Batch processing complete. {summary['successful']}/{summary['total']} files processed successfully.")
            logger.info(f"Summary saved to {summary_path}")
            
        else:
            # Process single file
            logger.info(f"Processing file: {input_file}")
            
            # Process the file through our workflow
            result = process_invoice(
                file_path=input_file,
                output_path=output_file,
                ocr_languages=lang_list,
                debug=verbose
            )
            
            if result["success"]:
                logger.info(f"Successfully extracted data from {input_file} to {output_file}")
                
                # Print summary of validation and consistency checks
                valid_fields = sum(1 for field in result["validation"].get("fields", {}).values() 
                                  if field.get("valid", False))
                total_fields = len(result["validation"].get("fields", {}))
                
                valid_checks = sum(1 for check in result["consistency"].get("checks", {}).values() 
                                  if check.get("valid", False))
                total_checks = len(result["consistency"].get("checks", {}))
                
                logger.info(f"Validation: {valid_fields}/{total_fields} fields valid")
                logger.info(f"Consistency: {valid_checks}/{total_checks} checks passed")
            else:
                logger.error(f"Extraction failed: {', '.join(result.get('errors', ['Unknown error']))}")
                sys.exit(1)
        
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        if verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)
