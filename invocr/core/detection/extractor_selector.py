"""
Dynamic extractor selection system based on document characteristics.

This module provides a framework for dynamically selecting the most appropriate
extractor implementation based on document type, format, and other characteristics.
"""

from typing import Dict, Any, Optional, Type, List
import logging
from abc import ABC, abstractmethod

from invocr.core.detection.document_detector import detect_document_type
from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor
from invocr.formats.pdf.extractors.pdf_invoice_extractor import PDFInvoiceExtractor
from invocr.extractors.specialized.adobe_extractor import AdobeInvoiceExtractor

logger = logging.getLogger(__name__)


class ExtractorSelector:
    """
    Dynamic extractor selector based on document characteristics.
    
    This class implements a decision tree approach to select the most appropriate
    extractor for a given document based on its type, format, and other characteristics.
    """
    
    def __init__(self):
        """Initialize the extractor selector with default mappings."""
        # Map document types to extractor classes
        self.extractor_map: Dict[str, Type[BaseInvoiceExtractor]] = {
            "adobe_invoice": AdobeInvoiceExtractor,
            "invoice": PDFInvoiceExtractor,
            "receipt": PDFInvoiceExtractor,
            "credit_note": AdobeInvoiceExtractor,  # Use Adobe extractor for credit notes (refunds)
            "unknown": PDFInvoiceExtractor  # Default fallback
        }
        
        # Map document types to default extraction rules
        self.rules_map: Dict[str, Dict[str, str]] = {
            "receipt": {
                "invoice_number": r"Receipt\s+#?([0-9]{4}-[0-9]{4})",
                "issue_date": r"Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
                "total_amount": r"TOTAL:\s*\$?(\d+\.\d{2})",
                "tax_amount": r"TAX:\s*\$?(\d+\.\d{2})"
            },
            "invoice": {
                "invoice_number": r"Invoice\s+#?([A-Za-z0-9\-]+)",
                "issue_date": r"Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
                "due_date": r"Due\s+Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
                "total_amount": r"Total:\s*\$?(\d+\.\d{2})",
                "tax_amount": r"Tax:\s*\$?(\d+\.\d{2})"
            }
        }
        
    def select_extractor(self, text: str, document_type: Optional[str] = None, 
                        metadata: Optional[Dict[str, Any]] = None, 
                        rules: Optional[Dict] = None,
                        language: str = "en") -> BaseInvoiceExtractor:
        """
        Select the most appropriate extractor for the document.
        
        Args:
            text: Document text content
            document_type: Optional explicit document type
            metadata: Optional document metadata
            rules: Optional custom extraction rules
            language: Document language code
            
        Returns:
            An appropriate extractor instance
        """
        metadata = metadata or {}
        
        # Detect document type if not provided
        if not document_type:
            document_type = detect_document_type(text, metadata)
            
        logger.info(f"Selecting extractor for document type: {document_type}")
        
        # Get extractor class for this document type
        extractor_class = self.extractor_map.get(document_type, PDFInvoiceExtractor)
        
        # Get default rules for this document type
        default_rules = self.rules_map.get(document_type, {})
        
        # Merge custom rules with default rules
        merged_rules = default_rules.copy()
        if rules:
            merged_rules.update(rules)
            
        # Create extractor instance with appropriate parameters
        if document_type == "adobe_invoice" or document_type == "credit_note":
            # Adobe extractor needs OCR text
            extractor = extractor_class(ocr_text=text)
        else:
            # Standard extractors need rules
            extractor = extractor_class(rules=merged_rules)
            
        logger.info(f"Selected extractor: {extractor.__class__.__name__}")
        return extractor
        
    def register_extractor(self, document_type: str, extractor_class: Type[BaseInvoiceExtractor]) -> None:
        """
        Register a new extractor for a document type.
        
        Args:
            document_type: Document type identifier
            extractor_class: Extractor class to use for this document type
        """
        self.extractor_map[document_type] = extractor_class
        
    def register_rules(self, document_type: str, rules: Dict[str, str]) -> None:
        """
        Register extraction rules for a document type.
        
        Args:
            document_type: Document type identifier
            rules: Extraction rules for this document type
        """
        self.rules_map[document_type] = rules


# Create default extractor selector
default_selector = ExtractorSelector()


def create_extractor(text: str, document_type: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    rules: Optional[Dict] = None,
                    language: str = "en") -> BaseInvoiceExtractor:
    """
    Create an appropriate extractor based on document characteristics.
    
    Args:
        text: Document text content
        document_type: Optional document type
        metadata: Optional document metadata
        rules: Optional custom extraction rules
        language: Document language code
        
    Returns:
        An appropriate extractor instance
    """
    return default_selector.select_extractor(
        text=text,
        document_type=document_type,
        metadata=metadata,
        rules=rules,
        language=language
    )
