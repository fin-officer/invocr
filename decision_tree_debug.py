#!/usr/bin/env python3
"""
Decision Tree Debug Script

This script provides detailed logging of the decision tree process during invoice extraction.
It shows step-by-step how document detection, extractor selection, and data extraction work.
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("decision_tree_debug")

# Import invocr modules
try:
    from invocr.utils.ocr import extract_text
    from invocr.core.detection.document_detector import DocumentDetector
    from invocr.core.detection.extractor_selector import ExtractorSelector
    from invocr.core.validators.extraction_validator import ExtractionValidator
    from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor
    from invocr.extractors.specialized.adobe_extractor import AdobeInvoiceExtractor
    from invocr.formats.pdf.extractors.rule_based_extractor import RuleBasedExtractor
    from invocr.formats.pdf.extractors.pdf_invoice_extractor import PdfInvoiceExtractor
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure you're running this script from the project root directory")
    sys.exit(1)


class DecisionTreeDebugger:
    """Debug class for tracing the decision tree process"""
    
    def __init__(self):
        self.detector = DocumentDetector()
        self.selector = ExtractorSelector()
        self.validator = ExtractionValidator()
        self.step_count = 0
        
    def log_step(self, title: str, message: str = "", data: Any = None):
        """Log a step in the decision tree process"""
        self.step_count += 1
        logger.info(f"\n{'='*80}")
        logger.info(f"STEP {self.step_count}: {title}")
        if message:
            logger.info(f"{message}")
        if data:
            if isinstance(data, dict):
                logger.info(json.dumps(data, indent=2, default=str))
            else:
                logger.info(f"{data}")
        logger.info(f"{'='*80}\n")
    
    def process_file(self, file_path: str, languages: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process a file with detailed logging of each step in the decision tree
        
        Args:
            file_path: Path to the PDF file
            languages: List of languages for OCR
            
        Returns:
            Extracted invoice data
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {}
            
        self.log_step("Starting Processing", f"File: {file_path}")
        
        # Extract text from PDF
        self.log_step("Extracting Text", "Extracting text from PDF using OCR")
        ocr_text = extract_text(file_path, languages=languages)
        
        # Log a sample of the extracted text
        text_sample = ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text
        self.log_step("OCR Text Sample", "First 500 characters of extracted text:", text_sample)
        
        # Prepare metadata
        metadata = {
            "filename": os.path.basename(file_path),
            "file_extension": os.path.splitext(file_path)[1].lower(),
            "ocr_text_length": len(ocr_text),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        self.log_step("Document Metadata", "Metadata prepared for document detection:", metadata)
        
        # Detect document type
        self.log_step("Document Detection", "Detecting document type using patterns and metadata")
        doc_type, confidence, features = self.detector.detect_document_type(ocr_text, metadata)
        
        detection_results = {
            "document_type": doc_type,
            "confidence": confidence,
            "detected_features": features
        }
        self.log_step("Detection Results", "Document detection results:", detection_results)
        
        # Select appropriate extractor
        self.log_step("Extractor Selection", "Selecting appropriate extractor based on document type and features")
        extractor = self.selector.select_extractor(doc_type, ocr_text, metadata, features)
        
        extractor_info = {
            "extractor_type": type(extractor).__name__,
            "extractor_module": type(extractor).__module__,
            "specialized": not isinstance(extractor, (PdfInvoiceExtractor, RuleBasedExtractor))
        }
        self.log_step("Selected Extractor", "Extractor selection results:", extractor_info)
        
        # Extract data
        self.log_step("Data Extraction", f"Extracting data using {type(extractor).__name__}")
        try:
            # Track start time for performance measurement
            start_time = time.time()
            
            # Extract invoice data
            if isinstance(extractor, AdobeInvoiceExtractor):
                invoice_data = extractor.extract_invoice_data(ocr_text, document_type=doc_type)
            elif isinstance(extractor, BaseInvoiceExtractor):
                invoice_data = extractor.extract_invoice_data(ocr_text, document_type=doc_type)
            else:
                # Generic fallback
                invoice_data = extractor.extract(ocr_text)
                
            # Calculate extraction time
            extraction_time = time.time() - start_time
            
            extraction_stats = {
                "extraction_time_seconds": extraction_time,
                "fields_extracted": len(invoice_data) if isinstance(invoice_data, dict) else "unknown",
                "items_extracted": len(invoice_data.get("items", [])) if isinstance(invoice_data, dict) else 0
            }
            self.log_step("Extraction Stats", "Extraction performance metrics:", extraction_stats)
            
        except Exception as e:
            logger.error(f"Error during extraction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
        
        # Validate extraction results
        self.log_step("Validation", "Validating extracted data against OCR text")
        validation_results = self.validator.validate(invoice_data, ocr_text)
        
        validation_summary = {
            "is_valid": validation_results.get("is_valid", False),
            "overall_confidence": validation_results.get("overall_confidence", 0),
            "field_confidence": validation_results.get("field_confidence", {}),
            "issues": validation_results.get("consistency_issues", [])
        }
        self.log_step("Validation Results", "Data validation results:", validation_summary)
        
        # Add validation results to invoice data
        invoice_data["validation"] = validation_results
        
        # Log final extracted data
        self.log_step("Final Extraction Results", "Complete extracted invoice data:", invoice_data)
        
        return invoice_data


def main():
    """Main function to run the debug script"""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_file_path> [output_json_path]")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Create debugger
    debugger = DecisionTreeDebugger()
    
    # Process file with detailed logging
    print(f"\n{'*'*100}")
    print(f"DECISION TREE DEBUG: Processing {pdf_path}")
    print(f"{'*'*100}\n")
    
    # Use multiple languages for better OCR results
    languages = ["eng", "pol", "est", "deu"]
    invoice_data = debugger.process_file(pdf_path, languages=languages)
    
    # Save results if output path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(invoice_data, f, indent=2, default=str)
        print(f"\nResults saved to {output_path}")
    
    # Final summary
    print(f"\n{'*'*100}")
    print(f"PROCESSING COMPLETE: {'Success' if invoice_data and 'error' not in invoice_data else 'Failed'}")
    print(f"{'*'*100}\n")


if __name__ == "__main__":
    main()
