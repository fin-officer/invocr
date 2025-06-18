"""
Debug command module.

Handles the 'debug' command for detailed debugging of extraction process.
"""

import os
import sys
import json
import click
import logging
from pathlib import Path

from invocr.utils.logger import get_logger
from invocr.utils.ocr import extract_text
from invocr.core.detection.document_detector import DocumentDetector
from invocr.core.detection.extractor_selector import ExtractorSelector
from invocr.core.validators.extraction_validator import validate_extraction
from ..common import load_yaml_config

logger = get_logger(__name__)


@click.command(name='debug')
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path(), required=False)
@click.option('-l', '--languages', help='OCR languages (e.g., en,pl,de)')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose logging')
def debug_command(input_file, output_file, languages, verbose):
    """
    Run detailed debugging of extraction process for a document.
    
    This command provides step-by-step logging of the document processing pipeline,
    including OCR extraction, document type detection, extractor selection, and validation.
    """
    if verbose:
        # Configure detailed logging for debug mode
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    debug_logger = get_logger("debug")
    
    # Print header
    debug_logger.info("*" * 100)
    debug_logger.info(f"SIMPLE DEBUG: Processing {input_file}")
    debug_logger.info("*" * 100)
    
    step = 1
    
    def log_step(step_num, title, message="", data=None):
        """Log a step in the extraction process"""
        debug_logger.info(f"\n{'='*80}")
        debug_logger.info(f"STEP {step_num}: {title}")
        if message:
            debug_logger.info(f"{message}")
        if data:
            if isinstance(data, dict):
                debug_logger.info(json.dumps(data, indent=2, default=str))
            else:
                debug_logger.info(f"{data}")
        debug_logger.info(f"{'='*80}\n")
    
    try:
        # Step 1: Import modules
        log_step(step, "Importing Modules", "Attempting to import required modules")
        step += 1
        
        # Step 2: OCR Module
        log_step(step, "OCR Module", "Successfully imported OCR module")
        step += 1
        
        # Step 3: Extract text from document
        log_step(step, "Extracting Text", f"Extracting text from {input_file}")
        
        # Parse languages option
        ocr_languages = ["eng", "pol", "est", "deu"]
        if languages:
            ocr_languages = languages.split(',')
            
        # Extract text
        ocr_text = extract_text(input_file, languages=ocr_languages)
        text_sample = ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text
        log_step(step, "OCR Text Sample", "First 500 characters of extracted text:", text_sample)
        step += 1
        
        # Step 4: Document detection
        log_step(step, "Importing Document Detector", "Attempting to import document detector")
        detector = DocumentDetector()
        log_step(step, "Document Detector", "Successfully imported document detector")
        step += 1
        
        # Step 5: Detect document type
        log_step(step, "Document Detection", "Detecting document type")
        
        # Prepare metadata
        filename = os.path.basename(input_file)
        file_extension = os.path.splitext(filename)[1]
        metadata = {
            "filename": filename,
            "file_extension": file_extension
        }
        
        # Detect document type
        doc_type, confidence, features = detector.detect_document_type(ocr_text, metadata)
        
        # Log detection results
        detection_results = {
            "document_type": doc_type,
            "confidence": confidence,
            "detected_features": features
        }
        log_step(step, "Detection Results", "Document detection results:", detection_results)
        step += 1
        
        # Step 6: Extractor selection
        log_step(step, "Importing Extractor Selector", "Attempting to import extractor selector")
        selector = ExtractorSelector()
        log_step(step, "Extractor Selector", "Successfully imported extractor selector")
        step += 1
        
        # Step 7: Select appropriate extractor
        log_step(step, "Extractor Selection", "Selecting appropriate extractor")
        extractor = selector.select_extractor(doc_type, ocr_text, metadata)
        
        # Log extractor selection results
        extractor_results = {
            "extractor_type": extractor.__class__.__name__,
            "extractor_module": extractor.__class__.__module__
        }
        log_step(step, "Selected Extractor", "Extractor selection results:", extractor_results)
        step += 1
        
        # Step 8: Data extraction
        log_step(step, "Data Extraction", f"Extracting data using {extractor.__class__.__name__}")
        
        # Extract data
        import time
        start_time = time.time()
        invoice_data = extractor.extract(ocr_text)
        end_time = time.time()
        
        # Log extraction stats
        extraction_time = end_time - start_time
        fields_extracted = len([k for k, v in invoice_data.items() if v and k != "items"])
        items_extracted = len(invoice_data.get("items", []))
        
        extraction_stats = {
            "extraction_time_seconds": extraction_time,
            "fields_extracted": fields_extracted,
            "items_extracted": items_extracted
        }
        log_step(step, "Extraction Stats", "Extraction performance metrics:", extraction_stats)
        step += 1
        
        # Step 9: Log extracted data
        log_step(step, "Extracted Data", "Complete extracted invoice data:", invoice_data)
        step += 1
        
        # Step 10: Validation
        log_step(step, "Validation", "Attempting to validate extracted data")
        validation_results = validate_extraction(invoice_data, ocr_text)
        
        validation_summary = {
            "is_valid": validation_results.get("is_valid", False),
            "overall_confidence": validation_results.get("overall_confidence", 0),
            "issues": validation_results.get("consistency_issues", [])
        }
        log_step(step, "Validation Results", "Data validation results:", validation_summary)
        step += 1
        
        # Save results if output path provided
        if output_file:
            # Combine all results
            debug_results = {
                "document": {
                    "path": input_file,
                    "ocr_text_sample": text_sample
                },
                "detection": detection_results,
                "extractor": extractor_results,
                "extraction": {
                    "stats": extraction_stats,
                    "data": invoice_data
                },
                "validation": validation_summary
            }
            
            # Save to file
            with open(output_file, 'w') as f:
                json.dump(debug_results, f, indent=2, default=str)
            
            debug_logger.info(f"\nResults saved to {output_file}")
        
        # Print footer
        debug_logger.info("\n" + "*" * 100)
        debug_logger.info("PROCESSING COMPLETE")
        debug_logger.info("*" * 100)
        
    except Exception as e:
        debug_logger.error(f"Error: {str(e)}")
        import traceback
        debug_logger.error(traceback.format_exc())
        
        # Print footer
        debug_logger.info("\n" + "*" * 100)
        debug_logger.info("PROCESSING FAILED")
        debug_logger.info("*" * 100)
        
        return 1
    
    return 0
