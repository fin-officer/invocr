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
        
    def select_extractor(self, document_type: Optional[str] = None, 
                        text: str = "", 
                        metadata: Optional[Dict[str, Any]] = None, 
                        features: Optional[Dict[str, Any]] = None,
                        rules: Optional[Dict] = None) -> BaseInvoiceExtractor:
        """
        Select the most appropriate extractor for the document using a dynamic decision tree.
        
        Args:
            document_type: Document type identifier
            text: Document text content
            metadata: Document metadata
            features: Document features from detection
            rules: Custom extraction rules
            
        Returns:
            An appropriate extractor instance
        """
        metadata = metadata or {}
        features = features or {}
        
        # Log the selection process start
        logger.info(f"Starting extractor selection for document type: {document_type}")
        
        # STEP 1: Analyze document characteristics
        logger.info("STEP 1: Analyzing document characteristics")
        
        # Get language information
        language = "en"  # Default
        if features and 'language' in features:
            language = features['language'].get('primary', 'en')
            language_scores = features['language'].get('scores', {})
            logger.info(f"Detected primary language: {language} with scores: {language_scores}")
        
        # Get document structure
        has_tables = False
        if features and 'structure' in features:
            structure = features['structure']
            has_tables = len(structure.get('potential_tables', [])) > 0
            logger.info(f"Document structure: {len(structure.get('potential_tables', []))} tables detected")
        
        # STEP 2: Apply decision tree for extractor selection
        logger.info("STEP 2: Applying decision tree for extractor selection")
        
        # Decision: Check for specialized formats first
        if document_type == "adobe_invoice":
            logger.info("Decision: Adobe invoice format detected, selecting specialized extractor")
            extractor_class = AdobeInvoiceExtractor
        
        # Decision: Check for refund/credit documents
        elif document_type == "credit_note":
            logger.info("Decision: Credit note/refund detected, selecting specialized extractor")
            extractor_class = AdobeInvoiceExtractor
        
        # Decision: Check language-specific formats
        elif language in ["pl", "et", "de"] and has_tables:
            logger.info(f"Decision: Non-English ({language}) invoice with tables detected")
            # For now we use the generic extractor, but could use specialized ones in the future
            extractor_class = PDFInvoiceExtractor
        
        # Decision: Check for receipt format
        elif document_type == "receipt":
            logger.info("Decision: Receipt format detected")
            extractor_class = PDFInvoiceExtractor
        
        # Default fallback
        else:
            logger.info("Decision: Using default invoice extractor")
            extractor_class = self.extractor_map.get(document_type, PDFInvoiceExtractor)
        
        # STEP 3: Configure extractor with appropriate rules
        logger.info("STEP 3: Configuring extractor with appropriate rules")
        
        # Get default rules for this document type
        default_rules = self.rules_map.get(document_type, {})
        
        # Add language-specific rules if available
        language_rules = {}
        if language != "en":
            # In the future, we could load language-specific rules from configuration
            logger.info(f"Adding language-specific rules for {language}")
        
        # Merge all rules with priority: custom > language > default
        merged_rules = {}
        merged_rules.update(default_rules)
        merged_rules.update(language_rules)
        if rules:
            merged_rules.update(rules)
            
        # STEP 4: Create and configure extractor instance
        logger.info("STEP 4: Creating extractor instance")
        
        # Create extractor with appropriate parameters
        if document_type == "adobe_invoice" or document_type == "credit_note":
            # Adobe extractor needs OCR text
            logger.info("Creating specialized extractor with OCR text")
            extractor = extractor_class(ocr_text=text)
        else:
            # Standard extractors need rules
            logger.info(f"Creating standard extractor with {len(merged_rules)} rules")
            extractor = extractor_class(rules=merged_rules)
        
        # STEP 5: Final selection result
        logger.info(f"Selected extractor: {extractor.__class__.__name__}")
        
        # Return the configured extractor
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
                    sample_text: Optional[str] = None,
                    **kwargs) -> BaseInvoiceExtractor:
    """
    Create an appropriate extractor based on document characteristics.
    
    Args:
        text: Document text content
        document_type: Optional document type
        metadata: Optional document metadata
        rules: Optional custom extraction rules
        sample_text: Optional sample text for detection (if different from text)
        **kwargs: Additional parameters
        
    Returns:
        An appropriate extractor instance
    """
    # Use sample_text for detection if provided, otherwise use text
    detection_text = sample_text if sample_text else text
    
    # Detect document type if not provided
    if not document_type and detection_text:
        doc_type, confidence, features = detect_document_type(detection_text, metadata)
    else:
        doc_type = document_type or "unknown"
        features = {}
        
    logger.info(f"Creating extractor for document type: {doc_type}")
    
    # Select appropriate extractor
    return default_selector.select_extractor(
        document_type=doc_type,
        text=text,
        metadata=metadata,
        features=features,
        rules=rules
    )
