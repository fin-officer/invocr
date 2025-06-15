"""
Base extractor class for invoice data extraction.
"""
from typing import Dict, List, Optional, Any
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataExtractor:
    """Base class for extracting structured data from invoice text."""
    
    def __init__(self, languages: List[str] = None):
        """Initialize the DataExtractor with specified languages.
        
        Args:
            languages: List of language codes to support (default: ["en", "pl"])
        """
        self.languages = languages or ["en", "pl"]
        self.patterns = self._load_extraction_patterns()
        logger.info(f"Data extractor initialized for languages: {self.languages}")
    
    def extract_invoice_data(self, text: str, document_type: str = "invoice") -> Dict[str, Any]:
        """Extract structured data from invoice text.
        
        Args:
            text: Raw text from OCR
            document_type: Type of document (e.g., "invoice", "receipt")
            
        Returns:
            Dict containing structured invoice data
        """
        result = self._get_document_template(document_type)
        
        # Detect language if not specified
        language = self._detect_language(text)
        
        # Extract basic info
        basic_info = self._extract_basic_info(text, language)
        result.update(basic_info)
        
        # Extract parties (seller/buyer)
        parties = self._extract_parties(text, language)
        result.update(parties)
        
        # Extract line items
        items = self._extract_items(text, language)
        if items:
            result["items"] = items
        
        # Extract totals
        totals = self._extract_totals(text, language)
        if totals:
            result["totals"] = totals
        
        # Extract payment info
        payment_info = self._extract_payment_info(text, language)
        result.update(payment_info)
        
        # Clean and validate extracted data
        self._validate_and_clean(result)
        
        # Calculate confidence score
        result["confidence"] = self._calculate_confidence(result, text)
        
        return result
    
    def _get_document_template(self, doc_type: str) -> Dict[str, Any]:
        """Get base template for different document types."""
        return {
            "document_type": doc_type,
            "document_number": "",
            "issue_date": "",
            "due_date": "",
            "seller": {
                "name": "",
                "address": "",
                "tax_id": ""
            },
            "buyer": {
                "name": "",
                "address": "",
                "tax_id": ""
            },
            "items": [],
            "totals": {
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "total": 0.0
            },
            "payment_method": "",
            "bank_account": "",
            "notes": ""
        }
    
    def _load_extraction_patterns(self) -> Dict[str, Dict]:
        """Load extraction patterns for different languages and fields."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the document text."""
        # Simple language detection based on common words
        en_words = ["invoice", "date", "total", "subtotal"]
        pl_words = ["faktura", "data", "razem", "netto"]
        de_words = ["rechnung", "datum", "gesamt", "nettobetrag"]
        
        text_lower = text.lower()
        scores = {
            "en": sum(1 for word in en_words if word in text_lower),
            "pl": sum(1 for word in pl_words if word in text_lower),
            "de": sum(1 for word in de_words if word in text_lower)
        }
        
        detected = max(scores, key=scores.get)  # type: ignore
        return detected if scores[detected] > 0 else "en"
    
    def _extract_basic_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract basic document information."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _extract_parties(self, text: str, language: str) -> Dict[str, Dict[str, str]]:
        """Extract seller and buyer information."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _extract_items(self, text: str, language: str) -> List[Dict[str, Any]]:
        """Extract line items from text."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _extract_totals(self, text: str, language: str) -> Dict[str, float]:
        """Extract financial totals."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _extract_payment_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract payment method and bank account info."""
        return {}
    
    def _validate_and_clean(self, data: Dict[str, Any]) -> None:
        """Validate and clean extracted data."""
        # Clean numeric values
        if "totals" in data:
            for key, value in data["totals"].items():
                if isinstance(value, str):
                    try:
                        data["totals"][key] = float(value.replace(",", "."))
                    except ValueError:
                        data["totals"][key] = 0.0

        # Clean whitespace in text fields
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value.strip()
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, str):
                        value[subkey] = subvalue.strip()
    
    def _calculate_confidence(self, data: Dict[str, Any], text: str) -> float:
        """Calculate confidence score for the extracted data."""
        score = 0
        max_score = 10  # Total possible score
        
        # Basic document info
        if data.get("document_number"):
            score += 2
        if data.get("issue_date"):
            score += 1
            
        # Seller information
        seller = data.get("seller", {})
        if seller.get("name"):
            score += 1
        if seller.get("tax_id") or seller.get("address"):
            score += 1
            
        # Buyer information
        buyer = data.get("buyer", {})
        if buyer.get("name"):
            score += 1
        if buyer.get("tax_id") or buyer.get("address"):
            score += 1
            
        # Items and totals
        if data.get("items") and len(data["items"]) > 0:
            score += 2
        if data.get("totals", {}).get("total", 0) > 0:
            score += 2
            
        # Payment information
        if data.get("payment_method") or data.get("bank_account"):
            score += 1
            
        return min(score / max_score, 1.0)
    
    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse date string into ISO format (YYYY-MM-DD)."""
        if not date_str or not isinstance(date_str, str):
            return ""
            
        date_str = date_str.strip()
        date_formats = [
            "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y",
            "%Y.%m.%d", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
                
        return ""
