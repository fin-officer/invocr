"""
Workflow command module.

Handles the 'workflow' command for end-to-end invoice processing.
"""

import os
import sys
import json
import logging
import click
from pathlib import Path
from typing import List, Dict, Any

from invocr.utils.logger import get_logger
from invocr.core.workflow import ExtractionWorkflow
from invocr.formats.pdf.ocr_html_generator import pdf_to_html_with_quadrants as generate_html_with_ocr
from ..common import load_yaml_config

logger = get_logger(__name__)


@click.command(name='workflow')
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_dir', type=click.Path())
@click.option('-c', '--config', 'config_file', type=click.Path(exists=True),
              help='Path to YAML configuration file')
@click.option('-b', '--batch', is_flag=True, help='Process input as directory of files')
@click.option('-l', '--languages', help='OCR languages (e.g., eng,pol,deu)')
@click.option('-t', '--tolerance', type=float, default=0.01, 
              help='Tolerance for numerical consistency checks (default: 0.01)')
@click.option('-g', '--generate-html', is_flag=True, help='Generate HTML with OCR text')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
def workflow_command(input_file, output_dir, config_file, batch, languages, tolerance, generate_html, verbose):
    """
    Run complete invoice processing workflow.
    
    This command performs end-to-end invoice processing:
    1. OCR text extraction
    2. Document type detection
    3. Data extraction with appropriate extractor
    4. Field validation
    5. Cross-field consistency checking
    6. Optional HTML generation with OCR text
    
    Results are saved as JSON files in the output directory.
    """
    try:
        # Set up logging
        if verbose:
            # Configure root logger for verbose output
            logging.basicConfig(level=logging.DEBUG)
            logger.debug("Verbose logging enabled")
        
        # Load configuration if provided
        config = None
        if config_file:
            config = load_yaml_config(config_file)
            
            # Use config values if command-line options not provided
            if not languages and 'extraction' in config and 'languages' in config['extraction']:
                languages = ','.join(config['extraction']['languages'])
            
            if 'extraction' in config and 'tolerance' in config['extraction'] and tolerance == 0.01:
                tolerance = config['extraction']['tolerance']
                
            if not generate_html and 'output' in config and 'generate_html' in config['output']:
                generate_html = config['output']['generate_html']
        
        # Parse languages
        lang_list = None
        if languages:
            lang_list = [lang.strip() for lang in languages.split(',')]
        else:
            lang_list = ["eng"]  # Default to English
        
        logger.info(f"Using OCR languages: {', '.join(lang_list)}")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize workflow
        workflow = ExtractionWorkflow(
            ocr_languages=lang_list,
            consistency_tolerance=tolerance,
            debug=verbose
        )
        
        # Process in batch mode if specified
        if batch:
            if not os.path.isdir(input_file):
                logger.error(f"Batch mode requires input to be a directory: {input_file}")
                sys.exit(1)
                
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
            results = []
            for file_path in pdf_files:
                file_basename = os.path.splitext(os.path.basename(file_path))[0]
                output_path = os.path.join(output_dir, f"{file_basename}_result.json")
                
                # Process the file
                result = workflow.process_document(
                    file_path=file_path,
                    output_path=output_path,
                    save_ocr=True
                )
                results.append(result)
                
                # Generate HTML if requested
                if generate_html:
                    html_path = os.path.join(output_dir, f"{file_basename}_ocr.html")
                    logger.info(f"Generating HTML with OCR text: {html_path}")
                    
                    try:
                        generate_html_with_ocr(
                            pdf_path=file_path,
                            output_path=html_path,
                            languages=lang_list
                        )
                    except Exception as e:
                        logger.error(f"HTML generation failed: {str(e)}")
            
            # Write summary report
            summary = {
                "total": len(results),
                "successful": sum(1 for r in results if r.get("success", False)),
                "failed": sum(1 for r in results if not r.get("success", False)),
                "files": [{"file": r["file_path"], "success": r["success"]} for r in results]
            }
            
            summary_path = os.path.join(output_dir, "workflow_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
                
            logger.info(f"Workflow complete. {summary['successful']}/{summary['total']} files processed successfully.")
            logger.info(f"Summary saved to {summary_path}")
            
        else:
            # Process single file
            file_basename = os.path.splitext(os.path.basename(input_file))[0]
            output_path = os.path.join(output_dir, f"{file_basename}_result.json")
            
            logger.info(f"Processing file: {input_file}")
            
            # Process the file through our workflow
            result = workflow.process_document(
                file_path=input_file,
                output_path=output_path,
                save_ocr=True
            )
            
            # Generate HTML if requested
            if generate_html:
                html_path = os.path.join(output_dir, f"{file_basename}_ocr.html")
                logger.info(f"Generating HTML with OCR text: {html_path}")
                
                try:
                    generate_html_with_ocr(
                        pdf_path=input_file,
                        output_path=html_path,
                        languages=lang_list
                    )
                except Exception as e:
                    logger.error(f"HTML generation failed: {str(e)}")
            
            if result["success"]:
                logger.info(f"Successfully processed {input_file}")
                
                # Print summary of validation and consistency checks
                valid_fields = sum(1 for field in result["validation"].get("fields", {}).values() 
                                  if field.get("valid", False))
                total_fields = len(result["validation"].get("fields", {}))
                
                valid_checks = sum(1 for check in result["consistency"].get("checks", {}).values() 
                                  if check.get("valid", False))
                total_checks = len(result["consistency"].get("checks", {}))
                
                logger.info(f"Validation: {valid_fields}/{total_fields} fields valid")
                logger.info(f"Consistency: {valid_checks}/{total_checks} checks passed")
                logger.info(f"Results saved to {output_path}")
                
                if generate_html:
                    logger.info(f"HTML with OCR text saved to {html_path}")
            else:
                logger.error(f"Processing failed: {', '.join(result.get('errors', ['Unknown error']))}")
                sys.exit(1)
        
    except Exception as e:
        logger.error(f"Workflow error: {str(e)}")
        if verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)
