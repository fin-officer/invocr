"""
Extractor factory for selecting and creating PDF extractors based on document characteristics.

This module provides a factory for selecting the appropriate extractor implementation
based on the document type, format, and other characteristics.
"""

from typing import Dict, Optional, Any

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor
from invocr.formats.pdf.extractors.pdf_invoice_extractor import PDFInvoiceExtractor
from invocr.extractors.specialized.adobe_extractor import AdobeInvoiceExtractor

logger = get_logger(__name__)


class PDFExtractorFactory:
    """Factory for creating and selecting appropriate PDF extractors."""

    @staticmethod
    def create_extractor(document_type: str = "invoice", rules: Optional[Dict] = None,
                         language: str = "en", format_hints: Optional[Dict] = None) -> BaseInvoiceExtractor:
        """
        Create an appropriate extractor based on document characteristics.

        Args:
            document_type: Type of document ('invoice', 'receipt', 'adobe_json', etc.)
            rules: Optional custom extraction rules
            language: Document language code (default: 'en')
            format_hints: Additional hints about the document format

        Returns:
            An appropriate extractor instance
        """
        format_hints = format_hints or {}
        
        # Check for Adobe JSON invoice
        if document_type.lower() == "adobe_json" or (
            format_hints and format_hints.get("source") == "adobe"):
            logger.info("Creating Adobe invoice extractor")
            return AdobeInvoiceExtractor()
        
        # Check for receipt document type
        elif document_type.lower() == "receipt":
            logger.info("Creating receipt-specialized PDF extractor")
            receipt_rules = rules or {
                # Default receipt-specific extraction rules
                "invoice_number": r"Receipt\s+#?([0-9]{4}-[0-9]{4})",
                "issue_date": r"Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
                "total_amount": r"TOTAL:\s*\$?(\d+\.\d{2})",
                "tax_amount": r"TAX:\s*\$?(\d+\.\d{2})"
            }
            return PDFInvoiceExtractor(rules=receipt_rules)
        
        # Default to standard invoice extractor
        else:
            logger.info("Creating standard PDF invoice extractor")
            return PDFInvoiceExtractor(rules=rules)
    
    @staticmethod
    def detect_document_type(text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Detect the document type from text content and metadata.

        Args:
            text: Document text content
            metadata: Optional document metadata

        Returns:
            Document type string
        """
        metadata = metadata or {}
        
        # Check for Adobe JSON invoice based on metadata
        if metadata.get("source") == "adobe" or metadata.get("filename", "").startswith("Adobe_Transaction"):
            return "adobe_json"
        
        # Check for receipt indicators
        receipt_indicators = ["receipt", "register", "store", "cash", "groceries"]
        receipt_score = sum(1 for indicator in receipt_indicators if indicator.lower() in text.lower())
        
        # Check for invoice indicators
        invoice_indicators = ["invoice", "bill to", "payment terms", "due date", "purchase order"]
        invoice_score = sum(1 for indicator in invoice_indicators if indicator.lower() in text.lower())
        
        # Determine document type based on indicators
        if receipt_score > invoice_score:
            return "receipt"
        else:
            return "invoice"
