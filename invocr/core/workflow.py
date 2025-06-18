"""
Workflow orchestration for invoice extraction and validation.

This module provides high-level functions to orchestrate the entire
extraction workflow, from document loading to data validation and
consistency checking.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple

from invocr.utils.logger import get_logger
from invocr.utils.ocr import extract_text
from invocr.core.detection.document_detector import DocumentDetector
from invocr.formats.pdf.extractor_factory import ExtractorFactory
from invocr.formats.pdf.extractors.specialized.consistency_checker import ConsistencyChecker
from invocr.validation.extraction_validator import validate_extraction

logger = get_logger(__name__)


class ExtractionWorkflow:
    """
    Orchestrates the complete invoice extraction and validation workflow.
    
    This class coordinates the entire process of extracting data from
    invoice documents, including:
    - OCR text extraction
    - Document type detection
    - Extractor selection
    - Data extraction
    - Field validation
    - Cross-field consistency checking
    """
    
    def __init__(self, 
                 ocr_languages: List[str] = None,
                 consistency_tolerance: float = 0.01,
                 debug: bool = False):
        """
        Initialize the extraction workflow.
        
        Args:
            ocr_languages: Languages to use for OCR (default: ["eng"])
            consistency_tolerance: Tolerance for numerical consistency checks
            debug: Whether to enable debug logging
        """
        self.logger = logger
        self.debug = debug
        self.ocr_languages = ocr_languages or ["eng"]
        
        # Initialize components
        self.document_detector = DocumentDetector()
        self.extractor_factory = ExtractorFactory()
        self.consistency_checker = ConsistencyChecker(tolerance=consistency_tolerance)
        
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
    
    def log_step(self, step_name: str, message: str):
        """Log a workflow step with consistent formatting."""
        if self.debug:
            self.logger.info(f"[{step_name.upper()}] {message}")
    
    def process_document(self, 
                         file_path: str, 
                         output_path: Optional[str] = None,
                         save_ocr: bool = False) -> Dict[str, Any]:
        """
        Process a document through the complete extraction workflow.
        
        Args:
            file_path: Path to the document file
            output_path: Path to save extraction results (optional)
            save_ocr: Whether to save OCR text to a file
            
        Returns:
            Dictionary with extraction results and validation info
        """
        result = {
            "file_path": file_path,
            "success": False,
            "document_type": None,
            "extraction_data": {},
            "validation": {},
            "consistency": {},
            "errors": []
        }
        
        try:
            # Step 1: Extract OCR text
            self.log_step("ocr", f"Extracting text from {file_path}")
            ocr_text = extract_text(
                file_path, 
                languages=self.ocr_languages,
                include_page_markers=True
            )
            
            if save_ocr and output_path:
                ocr_file = os.path.join(
                    os.path.dirname(output_path),
                    f"{os.path.splitext(os.path.basename(file_path))[0]}_ocr.txt"
                )
                with open(ocr_file, "w", encoding="utf-8") as f:
                    f.write(ocr_text)
                self.log_step("ocr", f"OCR text saved to {ocr_file}")
            
            # Step 2: Detect document type
            self.log_step("detection", "Detecting document type")
            document_type = self.document_detector.detect_document_type(ocr_text)
            result["document_type"] = document_type
            self.log_step("detection", f"Detected document type: {document_type}")
            
            # Step 3: Select appropriate extractor
            self.log_step("extractor", f"Selecting extractor for {document_type}")
            extractor = self.extractor_factory.get_extractor(document_type)
            self.log_step("extractor", f"Selected extractor: {extractor.__class__.__name__}")
            
            # Step 4: Extract data
            self.log_step("extraction", "Extracting data from document")
            extraction_data = extractor.extract(ocr_text)
            result["extraction_data"] = extraction_data
            self.log_step("extraction", f"Extracted {len(extraction_data)} fields")
            
            # Step 5: Validate extraction
            self.log_step("validation", "Validating extracted data")
            validation_result = validate_extraction(extraction_data, ocr_text)
            result["validation"] = validation_result
            
            valid_fields = sum(1 for field in validation_result.get("fields", {}).values() 
                              if field.get("valid", False))
            total_fields = len(validation_result.get("fields", {}))
            
            self.log_step("validation", 
                         f"Validation complete: {valid_fields}/{total_fields} fields valid")
            
            # Step 6: Check consistency between fields
            self.log_step("consistency", "Checking cross-field consistency")
            consistency_result = self.consistency_checker.check_all(extraction_data)
            result["consistency"] = consistency_result
            
            valid_checks = sum(1 for check in consistency_result.get("checks", {}).values() 
                              if check.get("valid", False))
            total_checks = len(consistency_result.get("checks", {}))
            
            self.log_step("consistency", 
                         f"Consistency checks complete: {valid_checks}/{total_checks} checks passed")
            
            # Step 7: Determine overall success
            result["success"] = (
                validation_result.get("valid", False) and 
                consistency_result.get("overall_valid", False)
            )
            
            # Step 8: Save results if output path provided
            if output_path:
                import json
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, default=str)
                self.log_step("output", f"Results saved to {output_path}")
            
        except Exception as e:
            error_msg = f"Error processing document: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result["errors"].append(error_msg)
            result["success"] = False
        
        return result
    
    def batch_process(self, 
                      file_paths: List[str], 
                      output_dir: str = None) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch.
        
        Args:
            file_paths: List of paths to document files
            output_dir: Directory to save extraction results
            
        Returns:
            List of dictionaries with extraction results
        """
        results = []
        
        for file_path in file_paths:
            self.log_step("batch", f"Processing {file_path}")
            
            if output_dir:
                output_path = os.path.join(
                    output_dir,
                    f"{os.path.splitext(os.path.basename(file_path))[0]}_result.json"
                )
            else:
                output_path = None
                
            result = self.process_document(file_path, output_path)
            results.append(result)
            
            self.log_step("batch", 
                         f"Completed {file_path}: {'SUCCESS' if result['success'] else 'FAILED'}")
        
        return results


def process_invoice(file_path: str, 
                   output_path: Optional[str] = None,
                   ocr_languages: List[str] = None,
                   debug: bool = False) -> Dict[str, Any]:
    """
    Process a single invoice document.
    
    This is a convenience function that creates an ExtractionWorkflow
    instance and processes a single document.
    
    Args:
        file_path: Path to the document file
        output_path: Path to save extraction results (optional)
        ocr_languages: Languages to use for OCR (default: ["eng"])
        debug: Whether to enable debug logging
        
    Returns:
        Dictionary with extraction results and validation info
    """
    workflow = ExtractionWorkflow(
        ocr_languages=ocr_languages or ["eng"],
        debug=debug
    )
    return workflow.process_document(file_path, output_path)


def batch_process_invoices(file_paths: List[str], 
                          output_dir: Optional[str] = None,
                          ocr_languages: List[str] = None,
                          debug: bool = False) -> List[Dict[str, Any]]:
    """
    Process multiple invoice documents in batch.
    
    This is a convenience function that creates an ExtractionWorkflow
    instance and processes multiple documents.
    
    Args:
        file_paths: List of paths to document files
        output_dir: Directory to save extraction results
        ocr_languages: Languages to use for OCR (default: ["eng"])
        debug: Whether to enable debug logging
        
    Returns:
        List of dictionaries with extraction results
    """
    workflow = ExtractionWorkflow(
        ocr_languages=ocr_languages or ["eng"],
        debug=debug
    )
    return workflow.batch_process(file_paths, output_dir)
