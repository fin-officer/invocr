"""
PDF data extraction utilities
Functions for extracting structured data from PDF text
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from ...utils.logger import get_logger

logger = get_logger(__name__)

# Regular expression patterns for various data elements
DOCUMENT_NUMBER_PATTERNS = [
    r"Invoice\s+Number\s*[:#]?\s*([A-Z0-9-]+)",
    r"(?:Invoice|Bill|Receipt)\s*[#:]?\s*([A-Z0-9-]+)",
    r"(?:No\.?|Number|Nr\.?)\s*[:#]?\s*([A-Z0-9-]+)"
]

DATE_PATTERNS = [
    r"(?:Date|Dated|Issued?)\s*[:]?\s*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})",
    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
    r"Invoice\s+Date\s+(\d{1,2}-[A-Z]{3}-\d{4})"
]

DUE_DATE_PATTERNS = [
    r"(?:Due\s*Date|Payment\s*Due|Due)\s*[:]?\s*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})",
    r"(?:Due\s*Date|Payment\s*Due|Due)\s*[:]?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
]

SELLER_PATTERNS = [
    r"(?:From|Seller|Vendor|Provider)[\s:]+(.+?)(?=\s*(?:To|Buyer|Client|Customer|$))",
    r"(?:Bill From|Issuer)[\s:]+(.+?)(?=\s*(?:Bill To|Recipient|$))"
]

BUYER_PATTERNS = [
    r"(?:To|Bill To|Buyer|Client|Customer)[\s:]+(.+?)(?=\s*(?:From|Seller|Vendor|$))",
    r"(?:Ship To|Recipient)[\s:]+(.+?)(?=\s*(?:From|Issuer|$))"
]

TOTAL_PATTERNS = [
    r"(?:Total|Amount Due|Balance Due|Grand Total)\s*[:]?\s*([0-9,.]+)",
    r"(?i)(?:total|amount)[\s:]*\$?\s*([\d,.]+)",
    r"TOTAL\s+([\d,.]+)"
]

SUBTOTAL_PATTERNS = [
    r"(?:Sub-?total|Net Amount)\s*[:]?\s*([0-9,.]+)",
    r"(?i)sub-?total[\s:]*\$?\s*([\d,.]+)",
    r"NET AMOUNT\s*\(?[A-Z]{3}\)?\s*([\d,.]+)"
]

TAX_PATTERNS = [
    r"(?:VAT|TAX|GST|Sales Tax)\s*[:]?\s*([0-9,.]+)",
    r"(?i)(?:vat|tax|gst)[\s:]*\$?\s*([\d,.]+)",
    r"TAXES\s*\(?[A-Z]{3}\)?\s*([\d,.]+)"
]

PAYMENT_METHOD_PATTERNS = [
    r"(?:Payment Method|Paid by|Payment by)[\s:]+(.+?)(?=\s*(?:\n|$))",
    r"(?:Payment Method|Paid by|Payment by)[\s:]+(?:Credit Card|Bank Transfer|Cash|Check|PayPal|Stripe)"
]

BANK_ACCOUNT_PATTERNS = [
    r"(?:Account|IBAN|Bank Account|Account Number)[\s:]+([A-Z0-9\s-]+(?:\s*[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30})?)(?=\s*(?:\n|$))"
]

NOTES_PATTERNS = [
    r"(?:Notes|Comments|Additional Information)[\s:]+(.+?)(?=\s*(?:\n\n|$))"
]

# Helper functions for data parsing
def parse_date(date_str: str) -> str:
    """
    Parse date string into ISO format (YYYY-MM-DD)
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        ISO formatted date string or original if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return ""
        
    date_formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
        "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d",
        "%d %b %Y", "%d %B %Y",
        "%b %d, %Y", "%B %d, %Y",
        "%d-%b-%Y", "%d-%B-%Y"
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return date_str.strip()

def parse_float(value_str: str) -> float:
    """
    Parse string into float, handling various formats
    
    Args:
        value_str: String representing a number
        
    Returns:
        Float value or 0.0 if parsing fails
    """
    if not value_str:
        return 0.0
        
    # Remove any non-numeric characters except for decimal point
    clean_str = re.sub(r"[^\d.]", "", str(value_str).replace(",", "."))
    
    try:
        # Handle multiple decimal points by keeping only the first one
        parts = clean_str.split('.')
        if len(parts) > 2:
            clean_str = parts[0] + '.' + ''.join(parts[1:])
        return float(clean_str) if clean_str else 0.0
    except (ValueError, TypeError):
        return 0.0


def extract_document_number(text: str) -> str:
    """
    Extract document number from text
    
    Args:
        text: Text to search for document number
        
    Returns:
        Extracted document number or empty string if not found
    """
    if not text:
        return ""
        
    for pattern in DOCUMENT_NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    
    return ""


def extract_date(text: str, date_type: str = "issue") -> str:
    """
    Extract date from text
    
    Args:
        text: Text to search for date
        date_type: Type of date to extract ('issue' or 'due')
        
    Returns:
        Extracted date in ISO format or empty string if not found
    """
    if not text:
        return ""
        
    patterns = DATE_PATTERNS if date_type == "issue" else DUE_DATE_PATTERNS
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            date_str = match.group(1).strip()
            return parse_date(date_str)
    
    return ""


def extract_party(text: str, party_type: str = "seller") -> Dict[str, str]:
    """
    Extract party information (seller or buyer) from text
    
    Args:
        text: Text to search for party information
        party_type: Type of party to extract ('seller' or 'buyer')
        
    Returns:
        Dictionary with party information
    """
    result = {"name": "", "address": "", "tax_id": ""}
    
    if not text or party_type not in ["seller", "buyer"]:
        return result
        
    patterns = SELLER_PATTERNS if party_type == "seller" else BUYER_PATTERNS
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            party_text = match.group(1).strip()
            if party_text:
                # First line is usually the name
                lines = [line.strip() for line in party_text.split('\n') if line.strip()]
                if lines:
                    result["name"] = lines[0]
                    # Rest is address
                    if len(lines) > 1:
                        result["address"] = " ".join(lines[1:])
            break
    
    # Try to extract tax ID
    tax_pattern = r"(?:VAT|TAX|GST|NIP|Tax ID)[\s:]+([A-Z0-9-]+)"
    tax_match = re.search(tax_pattern, text, re.IGNORECASE)
    if tax_match:
        result["tax_id"] = tax_match.group(1).strip()
    
    return result


def extract_items(text: str) -> List[Dict[str, Any]]:
    """
    Extract line items from text
    
    Args:
        text: Text to search for line items
        
    Returns:
        List of dictionaries with item details
    """
    items = []
    
    # Simple pattern for line items - this is a basic implementation
    # In a real application, you'd want more sophisticated parsing
    pattern = r"(\d+)\s+([^\n]+?)\s+(\d+(?:\.\d+)?)\s+([\d.,]+)\s+([\d.,]+)"
    matches = re.finditer(pattern, text, re.MULTILINE)
    
    for match in matches:
        try:
            items.append({
                "description": match.group(2).strip(),
                "quantity": parse_float(match.group(3)),
                "unit_price": parse_float(match.group(4)),
                "total_price": parse_float(match.group(5))
            })
        except (IndexError, ValueError):
            continue
    
    return items


def extract_totals(text: str) -> Dict[str, float]:
    """
    Extract totals from text
    
    Args:
        text: Text to search for totals
        
    Returns:
        Dictionary with total amounts
    """
    totals = {
        "subtotal": 0.0,
        "tax_amount": 0.0,
        "total": 0.0
    }
    
    # Extract subtotal
    for pattern in SUBTOTAL_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            totals["subtotal"] = parse_float(match.group(1))
            break
    
    # Extract tax amount
    for pattern in TAX_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            totals["tax_amount"] = parse_float(match.group(1))
            break
    
    # Extract total
    for pattern in TOTAL_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            totals["total"] = parse_float(match.group(1))
            break
    
    # If total is 0 but we have subtotal and tax, calculate total
    if totals["total"] == 0 and totals["subtotal"] > 0:
        totals["total"] = totals["subtotal"] + totals["tax_amount"]
    
    return totals


def extract_payment_terms(text: str) -> str:
    """
    Extract payment terms from text
    
    Args:
        text: Text to search for payment terms
        
    Returns:
        Extracted payment terms or empty string if not found
    """
    if not text:
        return ""
        
    for pattern in PAYMENT_METHOD_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip() if match.lastindex else match.group(0).strip()
    
    return ""


def extract_notes(text: str) -> str:
    """
    Extract notes or additional information from text
    
    Args:
        text: Text to search for notes
        
    Returns:
        Extracted notes or empty string if not found
    """
    if not text:
        return ""
        
    for pattern in NOTES_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip() if match.lastindex else ""
    
    return ""
