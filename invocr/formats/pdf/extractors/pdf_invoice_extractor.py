"""
PDF Invoice Extractor.

This module contains the main PDF invoice extractor implementation that leverages
the base extractor and utility modules for more maintainable extraction logic.
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor
from invocr.formats.pdf.extractors.date_utils import extract_date, parse_date
from invocr.formats.pdf.extractors.numeric_utils import parse_float, extract_currency
from invocr.formats.pdf.extractors.item_utils import extract_items
from invocr.formats.pdf.extractors.totals_utils import extract_totals

logger = get_logger(__name__)


class PDFInvoiceExtractor(BaseInvoiceExtractor):
    """
    Enhanced PDF invoice extractor with detailed extraction capabilities.
    
    This class extends the BaseInvoiceExtractor with additional extraction methods
    for party information, payment details, and more complex invoice structures.
    """
    
    def __init__(self, rules: Optional[Dict] = None):
        """
        Initialize the PDF invoice extractor.
        
        Args:
            rules: Optional dictionary of regex rules for extraction
        """
        super().__init__(rules)
    
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract invoice data from text with enhanced party and payment information.
        
        Args:
            text: The text content to extract from
            
        Returns:
            Dictionary containing extracted invoice data
        """
        # Get basic invoice data from base extractor
        invoice = super().extract(text)
        
        # Extract additional information
        seller, buyer = self._extract_parties(text)
        invoice["seller"] = seller
        invoice["buyer"] = buyer
        
        payment_info = self._extract_payment_information(text)
        invoice.update(payment_info)
        
        # Additional metadata
        invoice["metadata"] = self._extract_metadata(text)
        
        return invoice
    
    def _extract_parties(self, text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract seller and buyer information from invoice text.
        
        Args:
            text: The text content to extract from
            
        Returns:
            Tuple of (seller_info, buyer_info) dictionaries
        """
        seller = {
            "name": "",
            "address": "",
            "tax_id": "",
            "registration_number": "",
            "phone": "",
            "email": ""
        }
        
        buyer = {
            "name": "",
            "address": "",
            "tax_id": "",
            "registration_number": "",
            "phone": "",
            "email": ""
        }
        
        # Extract seller information
        seller_patterns = [
            # Seller name
            (r"(?i)(?:seller|provider|supplier|from|vendor|company|biller)[\s:]+([^\n]+)", "name"),
            # Seller address
            (r"(?i)(?:address|location)[\s:]+([^\n]+(?:\n[^\n]+){0,3})", "address"),
            # Seller tax ID
            (r"(?i)(?:tax\s+id|vat\s+number|vat\s+reg|gst\s+reg)[\s:]+([A-Z0-9\-]+)", "tax_id"),
            # Seller registration number
            (r"(?i)(?:company\s+reg|reg\s+no|registration)[\s:]+([A-Z0-9\-]+)", "registration_number"),
            # Seller phone
            (r"(?i)(?:phone|tel|telephone)[\s:]+([0-9\+\-\s\(\)\.]{7,20})", "phone"),
            # Seller email
            (r"(?i)(?:email|e-mail)[\s:]+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", "email")
        ]
        
        for pattern, field in seller_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                seller[field] = match.group(1).strip()
        
        # Extract buyer information
        buyer_patterns = [
            # Buyer name
            (r"(?i)(?:bill\s+to|buyer|customer|client|recipient)[\s:]+([^\n]+)", "name"),
            # Buyer address
            (r"(?i)(?:bill\s+to|buyer|customer|client)[\s:]+(?:[^\n]+\n)([^\n]+(?:\n[^\n]+){0,3})", "address"),
            # Buyer tax ID
            (r"(?i)(?:customer\s+tax\s+id|buyer\s+vat)[\s:]+([A-Z0-9\-]+)", "tax_id"),
            # Buyer registration number
            (r"(?i)(?:buyer\s+reg|customer\s+no)[\s:]+([A-Z0-9\-]+)", "registration_number"),
            # Buyer phone
            (r"(?i)(?:customer\s+phone|buyer\s+tel)[\s:]+([0-9\+\-\s\(\)\.]{7,20})", "phone"),
            # Buyer email
            (r"(?i)(?:customer\s+email|buyer\s+e-mail)[\s:]+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", "email")
        ]
        
        for pattern, field in buyer_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                buyer[field] = match.group(1).strip()
        
        return seller, buyer
    
    def _extract_payment_information(self, text: str) -> Dict[str, Any]:
        """
        Extract payment information from invoice text.
        
        Args:
            text: The text content to extract from
            
        Returns:
            Dictionary with payment information
        """
        payment_info = {
            "payment_method": "",
            "payment_status": "",
            "bank_account": "",
            "bank_name": "",
            "bank_swift": ""
        }
        
        # Payment method
        payment_method_patterns = [
            r"(?i)(?:payment\s+method|method\s+of\s+payment)[\s:]+([^\n]+)",
            r"(?i)(?:paid\s+by|pay\s+by|payment\s+via)[\s:]+([^\n]+)"
        ]
        
        for pattern in payment_method_patterns:
            match = re.search(pattern, text)
            if match:
                payment_info["payment_method"] = match.group(1).strip()
                break
        
        # Payment status
        status_patterns = [
            r"(?i)(paid|payment\s+received|payment\s+completed)",
            r"(?i)(due|unpaid|pending\s+payment)",
            r"(?i)(?:status|payment\s+status)[\s:]+([^\n]+)"
        ]
        
        for pattern in status_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) > 1:  # If there are multiple groups
                    payment_info["payment_status"] = match.group(2).strip()
                else:
                    status = match.group(1).strip().lower()
                    if any(term in status for term in ["paid", "received", "completed"]):
                        payment_info["payment_status"] = "Paid"
                    else:
                        payment_info["payment_status"] = "Unpaid"
                break
        
        # Bank account details
        bank_patterns = [
            (r"(?i)(?:account|iban|account\s+no)[\s:]+([A-Z0-9\s]{10,34})", "bank_account"),
            (r"(?i)(?:bank\s+name)[\s:]+([^\n]+)", "bank_name"),
            (r"(?i)(?:swift|bic)[\s:]+([A-Z0-9]{8,11})", "bank_swift"),
        ]
        
        for pattern, field in bank_patterns:
            match = re.search(pattern, text)
            if match:
                payment_info[field] = match.group(1).strip()
        
        return payment_info
    
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract additional metadata from invoice text.
        
        Args:
            text: The text content to extract from
            
        Returns:
            Dictionary with metadata
        """
        metadata = {
            "order_number": "",
            "reference_number": "",
            "delivery_date": None,
            "invoice_type": "",
            "discount": 0.0,
            "shipping": 0.0
        }
        
        # Order number
        order_patterns = [
            r"(?i)(?:order|po|purchase\s+order)[\s:]+#?\s*([A-Z0-9-]+)",
            r"(?i)(?:order|po|purchase\s+order)\s*(?:number|#|no\.?)[\s:]+([A-Z0-9-]+)"
        ]
        
        for pattern in order_patterns:
            match = re.search(pattern, text)
            if match:
                metadata["order_number"] = match.group(1).strip()
                break
        
        # Reference number
        ref_patterns = [
            r"(?i)(?:reference|ref)[\s:]+#?\s*([A-Z0-9-]+)",
            r"(?i)(?:reference|ref)\s*(?:number|#|no\.?)[\s:]+([A-Z0-9-]+)"
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, text)
            if match:
                metadata["reference_number"] = match.group(1).strip()
                break
        
        # Delivery date
        delivery_patterns = [
            r"(?i)(?:delivery\s+date|shipped\s+date|dispatch\s+date)[\s:]+(\d{1,2}[-/\\.]\d{1,2}[-/\\.]\d{2,4})"
        ]
        
        for pattern in delivery_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                parsed_date = parse_date(date_str)
                if parsed_date:
                    metadata["delivery_date"] = parsed_date.date()
                break
        
        # Invoice type
        type_patterns = [
            r"(?i)(invoice|receipt|bill|statement|debit\s+note|credit\s+note)",
            r"(?i)(?:document\s+type|invoice\s+type)[\s:]+([^\n]+)"
        ]
        
        for pattern in type_patterns:
            match = re.search(pattern, text)
            if match:
                if "type" in pattern:
                    metadata["invoice_type"] = match.group(1).strip().title()
                else:
                    metadata["invoice_type"] = match.group(1).strip().title()
                break
        
        # Discount
        discount_patterns = [
            r"(?i)(?:discount|reduction)[\s:]+([€$£]?\s*\d+(?:[,.]\d+)?)",
            r"(?i)(?:discount|reduction)[\s:]+(\d+(?:[,.]\d+)?%)"
        ]
        
        for pattern in discount_patterns:
            match = re.search(pattern, text)
            if match:
                discount_str = match.group(1)
                if "%" in discount_str:
                    # This is a percentage discount
                    percentage = parse_float(discount_str)
                    if "subtotal" in self and self["subtotal"] > 0:
                        metadata["discount"] = (percentage / 100) * self["subtotal"]
                else:
                    metadata["discount"] = parse_float(discount_str)
                break
        
        # Shipping
        shipping_patterns = [
            r"(?i)(?:shipping|freight|delivery|transport)[\s:]+([€$£]?\s*\d+(?:[,.]\d+)?)"
        ]
        
        for pattern in shipping_patterns:
            match = re.search(pattern, text)
            if match:
                shipping_str = match.group(1)
                metadata["shipping"] = parse_float(shipping_str)
                break
        
        return metadata
