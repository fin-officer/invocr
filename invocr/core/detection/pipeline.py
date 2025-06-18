"""
Invoice extraction pipeline with multi-level detection.

This module implements the main pipeline for invoice processing with multi-level
detection of document types, formats, and languages. The pipeline integrates
the decision tree framework with specialized extractors.
"""

from typing import Dict, Any, Optional
import os
import json
from pathlib import Path

from invocr.core.detection.decision_tree import InvoiceDetector, ExtractorSelector
from invocr.models import Invoice


class InvoiceExtractionPipeline:
    """
    Main processing pipeline that uses multi-level detection to extract invoice data.
    
    This pipeline processes invoice documents through a decision tree to determine
    the optimal extraction strategy based on document type, format, and language.
    It then applies the appropriate specialized extractor for accurate data extraction.
    """
    
    def __init__(self):
        """Initialize the extraction pipeline with detector and selectors."""
        self.detector = InvoiceDetector()
    
    def process(self, json_data: Dict[str, Any], ocr_text: Optional[str] = None) -> Invoice:
        """
        Process an invoice document and return extracted data.
        
        Args:
            json_data: The JSON data representing an invoice
            ocr_text: Optional OCR text for verification and improved extraction
            
        Returns:
            An Invoice object with extracted data
        """
        # Detect invoice type using decision tree
        detection_result = self.detector.detect(json_data, ocr_text)
        
        # Select appropriate extractor based on detection result
        extractor = ExtractorSelector.get_extractor(detection_result, ocr_text)
        
        # Extract data using the selected extractor
        invoice = extractor.extract(json_data)
        
        # Add detection metadata
        if not hasattr(invoice, "metadata"):
            invoice.metadata = {}
        invoice.metadata["detection"] = detection_result
        
        return invoice
    
    @staticmethod
    def process_file(json_path: str, ocr_path: Optional[str] = None) -> Invoice:
        """
        Process an invoice from a JSON file and optional OCR text file.
        
        Args:
            json_path: Path to the JSON file
            ocr_path: Optional path to OCR text file
            
        Returns:
            An Invoice object with extracted data
        """
        # Load JSON data
        with open(json_path, 'r') as f:
            json_data = json.load(f)
            
        # Add filename to metadata if not present
        if "_metadata" not in json_data:
            json_data["_metadata"] = {}
        json_data["_metadata"]["filename"] = Path(json_path).name
        
        # Load OCR text if provided
        ocr_text = None
        if ocr_path and os.path.exists(ocr_path):
            with open(ocr_path, 'r') as f:
                ocr_text = f.read()
        
        # Process through pipeline
        pipeline = InvoiceExtractionPipeline()
        return pipeline.process(json_data, ocr_text)
