"""
Base PDF invoice extractor.

This module contains the base extractor class that provides common functionality
for extracting data from PDF invoices using the specialized utility modules.
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.date_utils import extract_date
from invocr.formats.pdf.extractors.numeric_utils import extract_currency
from invocr.formats.pdf.extractors.item_utils import extract_items
from invocr.formats.pdf.extractors.totals_utils import extract_totals, calculate_totals_from_items, validate_totals

logger = get_logger(__name__)


class BaseInvoiceExtractor:
    """Base class for PDF invoice extractors."""
    
    def __init__(self, rules: Optional[Dict] = None):
        """
        Initialize the base extractor.
        
        Args:
            rules: Optional dictionary of regex rules for extraction
        """
        self.rules = rules or {}
        self.default_currency = "USD"  # Default currency if none detected

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract invoice data from text.
        
        Args:
            text: The text content to extract from
            
        Returns:
            Dictionary containing extracted invoice data
        """
        if not text:
            logger.warning("Empty text provided for extraction")
            return self._create_empty_invoice()
        
        logger.debug(f"Extracting invoice data from text ({len(text)} characters)")
        
        # Initialize invoice data structure
        invoice = self._create_empty_invoice()
        
        # Extract basic fields
        invoice["invoice_number"] = self._extract_invoice_number(text)
        invoice["issue_date"] = self._extract_issue_date(text)
        invoice["due_date"] = self._extract_due_date(text, invoice["issue_date"])
        
        # Extract line items
        invoice["items"] = self._extract_items(text)
        
        # Extract monetary values and validate
        extracted_totals = self._extract_totals(text)
        calculated_totals = calculate_totals_from_items(invoice["items"])
        validated_totals = validate_totals(extracted_totals, calculated_totals)
        
        # Update invoice with validated totals
        invoice["total_amount"] = validated_totals["total_amount"]
        invoice["subtotal"] = validated_totals["subtotal"]
        invoice["tax_amount"] = validated_totals["tax_amount"]
        invoice["currency"] = validated_totals["currency"] or self.default_currency
        
        # Extract other metadata
        invoice["payment_terms"] = self._extract_payment_terms(text)
        invoice["notes"] = self._extract_notes(text)
        
        # Post process to ensure consistency and fill in missing values
        invoice = self._post_process_invoice(invoice, text)
        
        return invoice
    
    def _create_empty_invoice(self) -> Dict[str, Any]:
        """Create an empty invoice data structure."""
        return {
            "invoice_number": "",
            "issue_date": None,
            "due_date": None,
            "currency": "",
            "total_amount": 0.0,
            "subtotal": 0.0,
            "tax_amount": 0.0,
            "items": [],
            "payment_terms": "",
            "notes": ""
        }
    
    def _extract_invoice_number(self, text: str) -> str:
        """Extract invoice number from text."""
        # Use custom rule if provided
        if "invoice_number" in self.rules:
            pattern = self.rules["invoice_number"]
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        
        # Common invoice number patterns
        patterns = [
            r"Invoice\s+Number\s*[:#]?\s*([A-Z0-9-]+)",
            r"(?:Invoice|Bill|Receipt)\s*[#:]?\s*([A-Z0-9-]+)",
            r"(?:No\.?|Number|Nr\.?)\s*[:#]?\s*([A-Z0-9-]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_issue_date(self, text: str) -> Optional[datetime]:
        """Extract issue date from text."""
        # Use custom rule if provided
        if "issue_date" in self.rules:
            pattern = self.rules["issue_date"]
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                date_str = match.group(1)
                parsed_date = extract_date(date_str)
                if parsed_date:
                    return parsed_date
        
        # Use the general date extraction utility
        return extract_date(text, date_type="issue")
    
    def _extract_due_date(self, text: str, issue_date: Optional[datetime]) -> Optional[datetime]:
        """Extract due date from text."""
        # Use custom rule if provided
        if "due_date" in self.rules:
            pattern = self.rules["due_date"]
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                date_str = match.group(1)
                parsed_date = extract_date(date_str)
                if parsed_date:
                    return parsed_date
        
        # Use the general date extraction utility
        return extract_date(text, date_type="due", reference_date=issue_date)
    
    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract line items from text."""
        # Use custom rule if provided
        if "items" in self.rules and callable(self.rules["items"]):
            items = self.rules["items"](text)
            if items:
                return items
        
        # Use the item extraction utility
        return extract_items(text)
    
    def _extract_totals(self, text: str) -> Dict[str, Any]:
        """Extract total amounts from text."""
        # Use custom rules if provided
        extracted_totals = {
            "total_amount": 0.0,
            "subtotal": 0.0,
            "tax_amount": 0.0,
            "tax_rate": 0.0,
            "currency": ""
        }
        
        # Use custom rules if available
        if "total_amount" in self.rules:
            pattern = self.rules["total_amount"]
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_totals["total_amount"] = float(match.group(1).replace(',', ''))
        
        if "subtotal" in self.rules:
            pattern = self.rules["subtotal"]
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_totals["subtotal"] = float(match.group(1).replace(',', ''))
        
        if "tax_amount" in self.rules:
            pattern = self.rules["tax_amount"]
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_totals["tax_amount"] = float(match.group(1).replace(',', ''))
        
        # If custom rules didn't extract everything, use the general utility
        if not all(extracted_totals.values()):
            utility_totals = extract_totals(text)
            
            # Only use utility values if custom rules didn't find them
            if extracted_totals["total_amount"] <= 0:
                extracted_totals["total_amount"] = utility_totals["total_amount"]
            
            if extracted_totals["subtotal"] <= 0:
                extracted_totals["subtotal"] = utility_totals["subtotal"]
            
            if extracted_totals["tax_amount"] <= 0:
                extracted_totals["tax_amount"] = utility_totals["tax_amount"]
            
            if extracted_totals["tax_rate"] <= 0:
                extracted_totals["tax_rate"] = utility_totals["tax_rate"]
            
            if not extracted_totals["currency"]:
                extracted_totals["currency"] = utility_totals["currency"]
        
        return extracted_totals
    
    def _extract_payment_terms(self, text: str) -> str:
        """Extract payment terms from text."""
        # Common payment terms patterns
        patterns = [
            r"(?i)(?:payment\s+terms|terms\s+of\s+payment|payment\s+condition)(?:s)?:?\s*(.+?)(?:\n|$)",
            r"(?i)(?:terms|payment):?\s*(.+?)(?:\n|$)",
            r"(?i)(?:due|payment)\s+(?:within|in)\s+(\d+)\s+days",
            r"(?i)(?:net|payment\s+due)\s+(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_notes(self, text: str) -> str:
        """Extract notes or additional information."""
        patterns = [
            r"(?i)(?:notes?|comment|remark|additional\s+information):?\s*(.+?)(?:\n\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _post_process_invoice(self, invoice: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Post-process the extracted invoice data for consistency.
        
        Args:
            invoice: The extracted invoice data
            text: The original text content
            
        Returns:
            Processed invoice data
        """
        # Ensure currency is set
        if not invoice["currency"]:
            invoice["currency"] = self._detect_currency(text) or self.default_currency
        
        # Compute missing totals
        if invoice["subtotal"] > 0 and invoice["tax_amount"] > 0 and invoice["total_amount"] == 0:
            invoice["total_amount"] = invoice["subtotal"] + invoice["tax_amount"]
        
        if invoice["items"] and invoice["subtotal"] == 0:
            # Calculate subtotal from items
            subtotal = sum(item["amount"] for item in invoice["items"] if "amount" in item)
            if subtotal > 0:
                invoice["subtotal"] = subtotal
        
        # Format dates as date objects instead of datetime objects
        if invoice["issue_date"]:
            invoice["issue_date"] = invoice["issue_date"].date()
        
        if invoice["due_date"]:
            invoice["due_date"] = invoice["due_date"].date()
        
        return invoice
    
    def _detect_currency(self, text: str) -> str:
        """Detect currency from text."""
        return extract_currency(text)
