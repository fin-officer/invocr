"""
Decision tree framework for multi-level invoice data detection.

This module implements a flexible decision tree structure for classifying invoices
by type, language, format, and other attributes. The tree allows for sequential
testing of document characteristics and making extraction decisions based on the results.
"""

from typing import Dict, Any, List, Callable, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass
import re


class InvoiceType(Enum):
    """Enum representing different invoice document types."""
    UNKNOWN = 0
    RECEIPT = 1
    ADOBE = 2
    STANDARD_INVOICE = 3
    CREDIT_NOTE = 4
    PURCHASE_ORDER = 5


class Language(Enum):
    """Enum representing supported languages for invoice processing."""
    UNKNOWN = 0
    EN = 1
    DE = 2
    FR = 3
    ES = 4
    PL = 5


@dataclass
class DetectionNode:
    """A node in the invoice detection decision tree.
    
    Each node contains a test function that evaluates document properties,
    and results/child nodes for both true and false outcomes of the test.
    """
    test_function: Callable[[Dict[str, Any], Optional[str]], bool]
    result_if_true: Any  # Could be another DetectionNode or a result value
    result_if_false: Any  # Could be another DetectionNode or a result value
    description: str = ""
    
    def evaluate(self, document: Dict[str, Any], ocr_text: Optional[str] = None) -> Any:
        """Evaluate this node's test function and return the appropriate result."""
        if self.test_function(document, ocr_text):
            result = self.result_if_true
        else:
            result = self.result_if_false
            
        # If the result is another node, evaluate it
        if isinstance(result, DetectionNode):
            return result.evaluate(document, ocr_text)
        
        # Otherwise return the result directly
        return result


class DocumentDetector:
    """Base class for document type detection."""
    
    def __init__(self):
        """Initialize the detector, building its decision tree structure."""
        self.root = None
        self._build_decision_tree()
    
    def _build_decision_tree(self):
        """Build the decision tree structure for document detection."""
        # Implement in subclasses
        pass
    
    def detect(self, document: Dict[str, Any], ocr_text: Optional[str] = None) -> Dict[str, Any]:
        """Process a document through the decision tree and return detection results."""
        if not self.root:
            return {"document_type": InvoiceType.UNKNOWN, "confidence": 0.0}
            
        result = self.root.evaluate(document, ocr_text)
        
        # Format the result into a standardized detection report
        if isinstance(result, InvoiceType):
            return {"document_type": result, "confidence": 1.0}
        elif isinstance(result, dict) and "document_type" in result:
            return result
        else:
            return {"document_type": InvoiceType.UNKNOWN, "confidence": 0.0}


class InvoiceDetector(DocumentDetector):
    """Multi-level decision tree for invoice type and format detection."""
    
    def _build_decision_tree(self):
        """Build the decision tree structure for invoice detection."""
        # Root level: Document type detection
        self.root = DetectionNode(
            test_function=self._is_adobe_invoice,
            result_if_true=self._adobe_subtree(),
            result_if_false=DetectionNode(
                test_function=self._is_receipt,
                result_if_true=self._receipt_subtree(),
                result_if_false=self._standard_invoice_subtree()
            ),
            description="Document type detection"
        )
    
    def _is_adobe_invoice(self, document: Dict[str, Any], ocr_text: Optional[str] = None) -> bool:
        """Check if the document is an Adobe invoice."""
        # Check metadata
        metadata = document.get("_metadata", {})
        filename = metadata.get("filename", "")
        
        if "Adobe_Transaction_No_" in filename:
            return True
            
        # Check OCR text
        if ocr_text and ("Adobe Systems" in ocr_text or "Adobe Inc." in ocr_text):
            return True
            
        # Check content patterns
        payment_terms = document.get("payment_terms", "")
        if "Adobe" in payment_terms:
            return True
            
        return False
    
    def _is_receipt(self, document: Dict[str, Any], ocr_text: Optional[str] = None) -> bool:
        """Check if the document is a receipt."""
        # Check metadata
        doc_type = document.get("_metadata", {}).get("document_type", "").lower()
        if "receipt" in doc_type:
            return True
            
        # Check for receipt-specific keywords in OCR text
        if ocr_text:
            receipt_keywords = [
                "receipt", "cash register", "till receipt", "store receipt",
                "thank you for shopping", "returns policy", "cashier", "register"
            ]
            
            for keyword in receipt_keywords:
                if keyword.lower() in ocr_text.lower():
                    return True
                    
        # Check for receipt structure
        if self._has_items_section(document, ocr_text) and not self._has_payment_terms(document, ocr_text):
            return True
            
        return False
    
    def _has_items_section(self, document: Dict[str, Any], ocr_text: Optional[str] = None) -> bool:
        """Check if the document has an items section typical for receipts."""
        if document.get("items"):
            return True
            
        if ocr_text:
            item_section_patterns = [
                r"item\s+qty\s+price",
                r"description\s+qty\s+price",
                r"items?\s+purchased",
                r"groceries",
                r"merchandise"
            ]
            
            for pattern in item_section_patterns:
                if re.search(pattern, ocr_text, re.IGNORECASE):
                    return True
                    
        return False
    
    def _has_payment_terms(self, document: Dict[str, Any], ocr_text: Optional[str] = None) -> bool:
        """Check if the document has payment terms typical for invoices."""
        if document.get("payment_terms"):
            return True
            
        if ocr_text:
            payment_terms_patterns = [
                r"payment terms",
                r"due date",
                r"net \d+ days",
                r"terms of payment"
            ]
            
            for pattern in payment_terms_patterns:
                if re.search(pattern, ocr_text, re.IGNORECASE):
                    return True
                    
        return False
    
    def _adobe_subtree(self) -> Union[InvoiceType, DetectionNode]:
        """Create Adobe invoice detection subtree for language determination."""
        return DetectionNode(
            test_function=self._detect_language,
            result_if_true=self._language_based_adobe_subtree(),
            result_if_false={"document_type": InvoiceType.ADOBE, "confidence": 0.9},
            description="Adobe invoice language detection"
        )
    
    def _receipt_subtree(self) -> Union[InvoiceType, DetectionNode]:
        """Create receipt detection subtree."""
        return DetectionNode(
            test_function=self._detect_language,
            result_if_true=self._language_based_receipt_subtree(),
            result_if_false={"document_type": InvoiceType.RECEIPT, "confidence": 0.8},
            description="Receipt language detection"
        )
    
    def _standard_invoice_subtree(self) -> Union[InvoiceType, DetectionNode]:
        """Create standard invoice detection subtree."""
        return DetectionNode(
            test_function=self._detect_language,
            result_if_true=self._language_based_invoice_subtree(),
            result_if_false={"document_type": InvoiceType.STANDARD_INVOICE, "confidence": 0.7},
            description="Standard invoice language detection"
        )
    
    def _detect_language(self, document: Dict[str, Any], ocr_text: Optional[str] = None) -> bool:
        """Detect document language."""
        # This is a placeholder - it always returns True to indicate language was detected
        # In a real implementation, this would use language detection models
        return True
    
    def _language_based_adobe_subtree(self) -> Dict[str, Any]:
        """Create language detection subtree for Adobe invoices."""
        return {"document_type": InvoiceType.ADOBE, "confidence": 1.0, "language": Language.EN}
    
    def _language_based_receipt_subtree(self) -> Dict[str, Any]:
        """Create language detection subtree for receipts."""
        return {"document_type": InvoiceType.RECEIPT, "confidence": 0.9, "language": Language.EN}
    
    def _language_based_invoice_subtree(self) -> Dict[str, Any]:
        """Create language detection subtree for standard invoices."""
        return {"document_type": InvoiceType.STANDARD_INVOICE, "confidence": 0.8, "language": Language.EN}


class ExtractorSelector:
    """Factory class that selects the appropriate extractor based on decision tree results."""
    
    @staticmethod
    def get_extractor(detection_result: Dict[str, Any], ocr_text: Optional[str] = None):
        """Factory method to return the appropriate extractor for the document type."""
        from invocr.extractors.specialized.adobe_extractor import AdobeInvoiceExtractor
        from invocr.formats.pdf.rule_based_extractor import RuleBasedExtractor
        
        doc_type = detection_result.get("document_type")
        
        if isinstance(doc_type, InvoiceType):
            if doc_type == InvoiceType.ADOBE:
                return AdobeInvoiceExtractor(ocr_text)
            elif doc_type == InvoiceType.RECEIPT:
                # Use RuleBasedExtractor with receipt-specific rules
                return RuleBasedExtractor(rules="receipt")
        
        # Default to rule-based extractor
        return RuleBasedExtractor()
