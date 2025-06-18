"""
Extraction workflow pipeline integrating dynamic document detection and validation.

This module provides a comprehensive extraction pipeline that combines
document detection, specialized extraction, and validation components
into a unified workflow.
"""

from typing import Dict, Any, Optional, List, Tuple
import logging
import os
from pathlib import Path

from invocr.core.detection.document_detector import detect_document_type
from invocr.core.detection.extractor_selector import create_extractor
from invocr.core.validators.extraction_validator import validate_extraction
from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """
    Comprehensive extraction pipeline with dynamic document detection and validation.
    
    This class implements a workflow that:
    1. Detects document type using the document detector
    2. Selects an appropriate extractor based on document characteristics
    3. Extracts data using the selected extractor
    4. Validates extraction results against OCR text
    5. Returns validated extraction results
    """
    
    def __init__(self, validate_results: bool = True):
        """
        Initialize the extraction pipeline.
        
        Args:
            validate_results: Whether to validate extraction results
        """
        self.validate_results = validate_results
        
    def process_document(self, text: str, metadata: Optional[Dict[str, Any]] = None,
                        rules: Optional[Dict] = None, language: str = "en") -> Dict[str, Any]:
        """
        Process a document through the extraction pipeline.
        
        Args:
            text: Document text content (OCR or extracted text)
            metadata: Optional document metadata
            rules: Optional custom extraction rules
            language: Document language code
            
        Returns:
            Dictionary with extraction results and validation info
        """
        metadata = metadata or {}
        
        # Step 1: Detect document type
        document_type = detect_document_type(text, metadata)
        logger.info(f"Detected document type: {document_type}")
        
        # Step 2: Select appropriate extractor
        extractor = create_extractor(
            text=text,
            document_type=document_type,
            metadata=metadata,
            rules=rules,
            language=language
        )
        logger.info(f"Selected extractor: {extractor.__class__.__name__}")
        
        # Step 3: Extract data
        extraction_result = self._extract_data(extractor, text, metadata)
        logger.info(f"Extraction completed with {len(extraction_result.get('items', []))} items")
        
        # Step 4: Validate results if requested
        if self.validate_results:
            validation_result = validate_extraction(extraction_result, text)
            logger.info(f"Validation completed with confidence: {validation_result['overall_confidence']:.2f}")
            
            # Add validation results to extraction results
            extraction_result["validation"] = validation_result
            
        return extraction_result
        
    def _extract_data(self, extractor: BaseInvoiceExtractor, text: str, 
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract data using the selected extractor.
        
        Args:
            extractor: Selected extractor instance
            text: Document text content
            metadata: Optional document metadata
            
        Returns:
            Extracted data dictionary
        """
        # Call appropriate extraction method based on extractor type
        if hasattr(extractor, "extract_invoice_data"):
            # Use standard extraction method
            return extractor.extract_invoice_data(text)
        elif hasattr(extractor, "extract"):
            # Use generic extract method
            return extractor.extract(text)
        else:
            # Fallback to direct attribute access
            logger.warning("Using fallback extraction method")
            invoice_data = {}
            
            # Extract common fields
            for field in ["invoice_number", "issue_date", "due_date", "currency", 
                         "supplier", "customer", "payment_terms"]:
                if hasattr(extractor, f"extract_{field}"):
                    invoice_data[field] = getattr(extractor, f"extract_{field}")(text)
                    
            # Extract items
            if hasattr(extractor, "extract_items"):
                invoice_data["items"] = extractor.extract_items(text)
                
            # Extract totals
            if hasattr(extractor, "extract_totals"):
                invoice_data["totals"] = extractor.extract_totals(text)
                
            return invoice_data


def process_document(text: str, metadata: Optional[Dict[str, Any]] = None,
                   rules: Optional[Dict] = None, language: str = "en",
                   validate: bool = True) -> Dict[str, Any]:
    """
    Process a document through the extraction pipeline.
    
    Args:
        text: Document text content (OCR or extracted text)
        metadata: Optional document metadata
        rules: Optional custom extraction rules
        language: Document language code
        validate: Whether to validate extraction results
        
    Returns:
        Dictionary with extraction results and validation info
    """
    pipeline = ExtractionPipeline(validate_results=validate)
    return pipeline.process_document(text, metadata, rules, language)


def process_file(file_path: str, ocr_text: Optional[str] = None,
               metadata: Optional[Dict[str, Any]] = None,
               rules: Optional[Dict] = None, language: str = "en",
               validate: bool = True) -> Dict[str, Any]:
    """
    Process a document file through the extraction pipeline.
    
    Args:
        file_path: Path to the document file
        ocr_text: Optional pre-extracted OCR text
        metadata: Optional document metadata
        rules: Optional custom extraction rules
        language: Document language code
        validate: Whether to validate extraction results
        
    Returns:
        Dictionary with extraction results and validation info
    """
    # Initialize metadata with file information
    if metadata is None:
        metadata = {}
        
    # Add file metadata
    file_path_obj = Path(file_path)
    metadata["filename"] = file_path_obj.name
    metadata["file_extension"] = file_path_obj.suffix.lower()
    metadata["file_size"] = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    
    # Get OCR text if not provided
    if ocr_text is None:
        from invocr.utils.ocr import extract_text
        ocr_text = extract_text(file_path)
        
    # Process document with OCR text
    return process_document(ocr_text, metadata, rules, language, validate)
