"""
Document classifier for intelligent extraction pipeline.

This module provides advanced document classification capabilities to determine
document type, format, and characteristics for dynamic extractor selection.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass

from invocr.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class DocumentFeatures:
    """Data class to store extracted document features for classification."""
    has_invoice_keywords: bool = False
    has_receipt_keywords: bool = False
    has_table_structure: bool = False
    has_vat_references: bool = False
    has_tax_id: bool = False
    has_payment_terms: bool = False
    has_line_items: bool = False
    has_delivery_info: bool = False
    has_purchase_order: bool = False
    language_indicators: Dict[str, int] = None
    
    def __post_init__(self):
        if self.language_indicators is None:
            self.language_indicators = {}


class DocumentClassifier:
    """
    Advanced document classifier that uses multiple signals to determine document type.
    
    This classifier analyzes text content, layout, keywords, and other features
    to classify documents into types (invoice, receipt, order, etc.) and subtypes.
    """
    
    # Document type keywords
    INVOICE_KEYWORDS = [
        "invoice", "faktura", "rechnung", "facture", "factura", 
        "bill to", "payment terms", "due date", "invoice date",
        "invoice number", "customer number", "account number"
    ]
    
    RECEIPT_KEYWORDS = [
        "receipt", "paragon", "quittung", "reçu", "recibo",
        "cash register", "store", "retail", "cashier", "terminal",
        "thank you for your purchase", "return policy"
    ]
    
    ORDER_KEYWORDS = [
        "order", "purchase order", "zamówienie", "bestellung", "commande", "pedido",
        "order number", "order date", "shipping method", "delivery date"
    ]
    
    # Language indicators
    LANGUAGE_INDICATORS = {
        "en": ["invoice", "receipt", "total", "payment", "date", "amount", "tax"],
        "pl": ["faktura", "paragon", "suma", "płatność", "data", "kwota", "podatek", "razem"],
        "de": ["rechnung", "quittung", "gesamt", "zahlung", "datum", "betrag", "steuer"],
        "fr": ["facture", "reçu", "total", "paiement", "date", "montant", "taxe"],
        "es": ["factura", "recibo", "total", "pago", "fecha", "importe", "impuesto"]
    }
    
    def __init__(self):
        """Initialize the document classifier."""
        self.logger = logger
    
    def extract_features(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentFeatures:
        """
        Extract classification features from document text and metadata.
        
        Args:
            text: The document text content
            metadata: Optional document metadata
            
        Returns:
            DocumentFeatures object with extracted features
        """
        features = DocumentFeatures()
        
        # Check for invoice keywords
        features.has_invoice_keywords = any(keyword.lower() in text.lower() 
                                           for keyword in self.INVOICE_KEYWORDS)
        
        # Check for receipt keywords
        features.has_receipt_keywords = any(keyword.lower() in text.lower() 
                                           for keyword in self.RECEIPT_KEYWORDS)
        
        # Check for table structure
        features.has_table_structure = self._detect_table_structure(text)
        
        # Check for VAT references
        features.has_vat_references = any(vat_term in text.lower() 
                                         for vat_term in ["vat", "tax", "mwst", "ust", "iva", "tva", "podatek"])
        
        # Check for tax ID
        tax_id_patterns = [
            r'\b[A-Z]{2}\d{9,12}\b',  # EU VAT format
            r'\b\d{3}-\d{2}-\d{4}\b',  # US SSN format
            r'\b\d{2}-\d{7}\b',        # PL NIP format
            r'\bTAX ID:?\s*([A-Z0-9\-]+)\b'  # Generic tax ID
        ]
        features.has_tax_id = any(re.search(pattern, text) for pattern in tax_id_patterns)
        
        # Check for payment terms
        payment_terms_patterns = [
            r'payment\s+terms',
            r'due\s+in\s+\d+\s+days',
            r'net\s+\d+',
            r'due\s+date',
            r'termin\s+płatności'
        ]
        features.has_payment_terms = any(re.search(pattern, text, re.IGNORECASE) 
                                        for pattern in payment_terms_patterns)
        
        # Check for line items
        line_item_patterns = [
            r'\b(qty|quantity|ilość)\b.*\b(price|cena)\b.*\b(amount|kwota)\b',
            r'\b\d+\s*x\s*[\d\.,]+\s*=\s*[\d\.,]+\b',
            r'\b(item|description|opis)\b.*\b(unit|price|cena)\b'
        ]
        features.has_line_items = any(re.search(pattern, text, re.IGNORECASE) 
                                     for pattern in line_item_patterns)
        
        # Detect language indicators
        language_scores = {}
        for lang, indicators in self.LANGUAGE_INDICATORS.items():
            score = sum(1 for indicator in indicators if indicator.lower() in text.lower())
            language_scores[lang] = score
        
        features.language_indicators = language_scores
        
        return features
    
    def _detect_table_structure(self, text: str) -> bool:
        """
        Detect if the document contains table-like structures.
        
        Args:
            text: The document text content
            
        Returns:
            True if table structures are detected, False otherwise
        """
        # Look for patterns that suggest table structures
        table_patterns = [
            r'\b(item|description|qty|quantity|price|amount|total)\b.*\n.*\b(item|description|qty|quantity|price|amount|total)\b',
            r'[-]{3,}.*[-]{3,}',  # Table separators
            r'[|]{1}.*[|]{1}',    # Pipe separators
            r'\b\d+\s*\|\s*[\w\s]+\s*\|\s*\d+\s*\|\s*[\d\.,]+\s*\|\s*[\d\.,]+\b'  # Typical table row
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE | re.MULTILINE) 
                  for pattern in table_patterns)
    
    def classify_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Classify the document based on its features.
        
        Args:
            text: The document text content
            metadata: Optional document metadata
            
        Returns:
            Tuple of (document_type, additional_attributes)
        """
        metadata = metadata or {}
        features = self.extract_features(text, metadata)
        
        # Check for Adobe JSON invoice based on metadata
        if metadata.get("source") == "adobe" or metadata.get("filename", "").startswith("Adobe_Transaction"):
            return "adobe_json", {"confidence": 0.95, "features": features}
        
        # Calculate scores for different document types
        invoice_score = sum([
            2 if features.has_invoice_keywords else 0,
            1 if features.has_vat_references else 0,
            1 if features.has_tax_id else 0,
            2 if features.has_payment_terms else 0,
            1 if features.has_line_items else 0,
            1 if features.has_table_structure else 0
        ])
        
        receipt_score = sum([
            2 if features.has_receipt_keywords else 0,
            1 if not features.has_payment_terms else 0,
            1 if not features.has_tax_id else 0,
            1 if features.has_table_structure else 0
        ])
        
        order_score = sum([
            2 if any(keyword.lower() in text.lower() for keyword in self.ORDER_KEYWORDS) else 0,
            1 if features.has_line_items else 0,
            1 if features.has_table_structure else 0,
            1 if features.has_delivery_info else 0
        ])
        
        # Determine document type based on scores
        doc_type = "invoice"  # Default
        confidence = 0.5
        
        if invoice_score > receipt_score and invoice_score > order_score:
            doc_type = "invoice"
            confidence = min(0.5 + (invoice_score / 10), 0.95)
        elif receipt_score > invoice_score and receipt_score > order_score:
            doc_type = "receipt"
            confidence = min(0.5 + (receipt_score / 8), 0.95)
        elif order_score > invoice_score and order_score > receipt_score:
            doc_type = "order"
            confidence = min(0.5 + (order_score / 8), 0.95)
        
        # Determine language
        language = max(features.language_indicators.items(), key=lambda x: x[1])[0]
        
        # Create additional attributes
        attributes = {
            "confidence": confidence,
            "language": language,
            "features": features,
            "has_tables": features.has_table_structure,
            "has_line_items": features.has_line_items
        }
        
        self.logger.info(f"Classified document as {doc_type} ({confidence:.2f} confidence)")
        return doc_type, attributes
