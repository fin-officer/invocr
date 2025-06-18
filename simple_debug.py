#!/usr/bin/env python3
"""
Simple Debug Script for Invoice Extraction

This script provides detailed logging of the extraction process for a PDF invoice.
"""

import os
import sys
import json
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("simple_debug")

def log_step(step_num, title, message="", data=None):
    """Log a step in the extraction process"""
    logger.info(f"\n{'='*80}")
    logger.info(f"STEP {step_num}: {title}")
    if message:
        logger.info(f"{message}")
    if data:
        if isinstance(data, dict):
            logger.info(json.dumps(data, indent=2, default=str))
        else:
            logger.info(f"{data}")
    logger.info(f"{'='*80}\n")

def main():
    """Main function to run the debug script"""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_file_path> [output_json_path]")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        sys.exit(1)
    
    # Print header
    print(f"\n{'*'*100}")
    print(f"SIMPLE DEBUG: Processing {pdf_path}")
    print(f"{'*'*100}\n")
    
    step = 1
    
    # Step 1: Import required modules
    try:
        log_step(step, "Importing Modules", "Attempting to import required modules")
        step += 1
        
        # Try importing OCR module
        from invocr.utils.ocr import extract_text
        log_step(step, "OCR Module", "Successfully imported OCR module")
        step += 1
        
        # Extract text from PDF
        log_step(step, "Extracting Text", f"Extracting text from {pdf_path}")
        languages = ["eng", "pol", "est", "deu"]
        ocr_text = extract_text(pdf_path, languages=languages)
        text_sample = ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text
        log_step(step, "OCR Text Sample", "First 500 characters of extracted text:", text_sample)
        step += 1
        
        # Try importing document detector
        log_step(step, "Importing Document Detector", "Attempting to import document detector")
        from invocr.core.detection.document_detector import DocumentDetector
        detector = DocumentDetector()
        log_step(step, "Document Detector", "Successfully imported document detector")
        step += 1
        
        # Detect document type
        log_step(step, "Document Detection", "Detecting document type")
        metadata = {
            "filename": os.path.basename(pdf_path),
            "file_extension": os.path.splitext(pdf_path)[1].lower(),
        }
        doc_type, confidence, features = detector.detect_document_type(ocr_text, metadata)
        detection_results = {
            "document_type": doc_type,
            "confidence": confidence,
            "detected_features": features
        }
        log_step(step, "Detection Results", "Document detection results:", detection_results)
        step += 1
        
        # Try importing extractor selector
        log_step(step, "Importing Extractor Selector", "Attempting to import extractor selector")
        from invocr.core.detection.extractor_selector import ExtractorSelector
        selector = ExtractorSelector()
        log_step(step, "Extractor Selector", "Successfully imported extractor selector")
        step += 1
        
        # Select appropriate extractor
        log_step(step, "Extractor Selection", "Selecting appropriate extractor")
        extractor = selector.select_extractor(doc_type, ocr_text, metadata, features)
        extractor_info = {
            "extractor_type": type(extractor).__name__,
            "extractor_module": type(extractor).__module__,
        }
        log_step(step, "Selected Extractor", "Extractor selection results:", extractor_info)
        step += 1
        
        # Extract data
        log_step(step, "Data Extraction", f"Extracting data using {type(extractor).__name__}")
        
        # Extract invoice data
        start_time = None
        end_time = None
        try:
            import time
            start_time = time.time()
            
            # Different extractors have different interfaces
            if hasattr(extractor, "extract_invoice_data"):
                invoice_data = extractor.extract_invoice_data(ocr_text, document_type=doc_type)
            else:
                invoice_data = extractor.extract(ocr_text)
                
            end_time = time.time()
            
            # Log extraction stats
            if start_time and end_time:
                extraction_time = end_time - start_time
                extraction_stats = {
                    "extraction_time_seconds": extraction_time,
                    "fields_extracted": len(invoice_data) if isinstance(invoice_data, dict) else "unknown",
                    "items_extracted": len(invoice_data.get("items", [])) if isinstance(invoice_data, dict) else 0
                }
                log_step(step, "Extraction Stats", "Extraction performance metrics:", extraction_stats)
                step += 1
            
            # Log extracted data
            log_step(step, "Extracted Data", "Complete extracted invoice data:", invoice_data)
            step += 1
            
            # Try validation if available
            try:
                log_step(step, "Validation", "Attempting to validate extracted data")
                from invocr.core.validators.extraction_validator import validate_extraction
                validation_results = validate_extraction(invoice_data, ocr_text)
                
                validation_summary = {
                    "is_valid": validation_results.get("is_valid", False),
                    "overall_confidence": validation_results.get("overall_confidence", 0),
                    "issues": validation_results.get("consistency_issues", [])
                }
                log_step(step, "Validation Results", "Data validation results:", validation_summary)
                step += 1
                
                # Add validation results to invoice data
                invoice_data["validation"] = validation_results
            except Exception as e:
                logger.error(f"Error during validation: {e}")
            
            # Save results if output path provided
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(invoice_data, f, indent=2, default=str)
                print(f"\nResults saved to {output_path}")
        
        except Exception as e:
            logger.error(f"Error during extraction: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Final summary
    print(f"\n{'*'*100}")
    print(f"PROCESSING COMPLETE")
    print(f"{'*'*100}\n")


if __name__ == "__main__":
    main()
