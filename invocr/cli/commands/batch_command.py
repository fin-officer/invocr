"""
Batch command module.

Handles the 'batch' command for processing multiple files.
"""

import os
import sys
import json
import click
import concurrent.futures
from pathlib import Path
from datetime import datetime

from invocr.utils.logger import get_logger
from invocr.core.converter import convert_document
from ..common import load_yaml_config, find_files, ensure_output_dir, get_matching_output_path, process_month_year_dir

logger = get_logger(__name__)


@click.command(name='batch')
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('output_dir', type=click.Path(file_okay=False, dir_okay=True))
@click.option('-f', '--format', 'output_format', type=click.Choice(['json', 'xml', 'html', 'pdf']),
              default='json', help='Output format')
@click.option('-l', '--languages', help='OCR languages (e.g., en,pl,de)')
@click.option('-c', '--config', 'config_file', type=click.Path(exists=True),
              help='Path to YAML configuration file')
@click.option('-e', '--extension', 'extensions', multiple=True, 
              help='Input file extensions to process (e.g., pdf,jpg,png)')
@click.option('-r', '--recursive', is_flag=True, help='Process directories recursively')
@click.option('-p', '--parallel', is_flag=True, help='Process files in parallel')
@click.option('-w', '--workers', type=int, default=4, help='Number of parallel workers')
@click.option('-m', '--month', type=int, help='Process files for specific month')
@click.option('-y', '--year', type=int, help='Process files for specific year')
def batch_command(input_dir, output_dir, output_format, languages, config_file, 
                 extensions, recursive, parallel, workers, month, year):
    """Process multiple files in batch mode"""
    try:
        # Load configuration if provided
        config = None
        if config_file:
            config = load_yaml_config(config_file)
            
            # Use config values if command-line options not provided
            if not output_format and 'output' in config and 'format' in config['output']:
                output_format = config['output']['format']
                
            if not languages and 'extraction' in config and 'languages' in config['extraction']:
                languages = ','.join(config['extraction']['languages'])
                
            if not parallel and 'processing' in config and 'parallel' in config['processing']:
                parallel = config['processing']['parallel']
                
            if workers == 4 and 'processing' in config and 'max_workers' in config['processing']:
                workers = config['processing']['max_workers']
        
        # Handle month/year specific processing
        if month and year:
            input_dir, output_dir = process_month_year_dir(os.getcwd(), month, year)
            logger.info(f"Processing month {month}/{year}")
            logger.info(f"Input directory: {input_dir}")
            logger.info(f"Output directory: {output_dir}")
        
        # Ensure output directory exists
        output_dir = ensure_output_dir(output_dir)
        
        # Default extensions if none provided
        if not extensions:
            extensions = ['pdf']
            
        # Find all input files
        files = find_files(input_dir, extensions, recursive)
        if not files:
            logger.warning(f"No files with extensions {extensions} found in {input_dir}")
            return
        
        logger.info(f"Found {len(files)} files to process")
        
        # Parse languages
        lang_list = None
        if languages:
            lang_list = [lang.strip() for lang in languages.split(',')]
            
        # Set proper output extension
        output_ext = f".{output_format}"
        
        # Process files
        if parallel and len(files) > 1:
            logger.info(f"Processing in parallel with {workers} workers")
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                futures = []
                for file_path in files:
                    output_path = get_matching_output_path(str(file_path), output_dir, output_ext)
                    futures.append(
                        executor.submit(
                            _process_single_file,
                            str(file_path),
                            output_path,
                            output_format,
                            lang_list
                        )
                    )
                    
                # Process results as they complete
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    # Each future.result() returns (success, file_path, error)
                    success, file_path, error = future.result()
                    _log_progress(i, len(files), file_path, success, error)
        else:
            # Process sequentially
            for i, file_path in enumerate(files, 1):
                output_path = get_matching_output_path(str(file_path), output_dir, output_ext)
                success, file_path, error = _process_single_file(str(file_path), output_path, output_format, lang_list)
                _log_progress(i, len(files), str(file_path), success, error)
                
        logger.info(f"Batch processing complete. Output saved to {output_dir}")
        
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


def _process_single_file(input_path, output_path, output_format, languages):
    """Process a single file and return result
    
    Returns:
        Tuple[bool, str, Optional[str]]: (success, file_path, error_message)
    """
    try:
        # Use the new extraction pipeline for processing
        from invocr.core.workflow.extraction_pipeline import process_file
        from invocr.utils.ocr import extract_text
        
        # Prepare metadata
        metadata = {
            "filename": os.path.basename(input_path),
            "file_extension": os.path.splitext(input_path)[1].lower(),
        }
        
        # Extract OCR text if needed
        ocr_text = None
        if languages:
            ocr_text = extract_text(input_path, languages=languages)
        
        # Process file through extraction pipeline with validation
        invoice_data = process_file(
            file_path=input_path,
            ocr_text=ocr_text,
            metadata=metadata,
            validate=True
        )
        
        # Write output to file based on format
        if output_format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(invoice_data, f, indent=2, default=str)
        else:
            # For other formats, fall back to convert_document
            success, error = convert_document(
                input_file=input_path,
                output_file=output_path,
                output_format=output_format,
                languages=languages
            )
            if not success:
                return False, input_path, error
        
        # Check validation results if available
        if "validation" in invoice_data:
            validation = invoice_data["validation"]
            if not validation.get("is_valid", True):
                warning = f"Validation issues detected (confidence: {validation.get('overall_confidence', 0):.2f})"
                logger.warning(warning)
                if validation.get("consistency_issues"):
                    for issue in validation["consistency_issues"]:
                        logger.warning(f"  - {issue}")
        
        return True, input_path, None
    except Exception as e:
        return False, input_path, str(e)


def _log_progress(current, total, file_path, success, error):
    """Log progress of batch processing"""
    file_name = os.path.basename(file_path)
    if success:
        logger.info(f"[{current}/{total}] Processed: {file_name}")
    else:
        logger.error(f"[{current}/{total}] Failed: {file_name} - {error}")
