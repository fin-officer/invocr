"""
PDF data extraction utilities
Functions for extracting structured data from PDF text
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from ...utils.logger import get_logger

logger = get_logger(__name__)

# Regular expression patterns for various data elements
DOCUMENT_NUMBER_PATTERNS = [
    r"Invoice\s+Number\s*[:#]?\s*([A-Z0-9-]+)",
    r"(?:Invoice|Bill|Receipt)\s*[#:]?\s*([A-Z0-9-]+)",
    r"(?:No\.?|Number|Nr\.?)\s*[:#]?\s*([A-Z0-9-]+)"
]

# Common date patterns for invoice dates
DATE_PATTERNS = [
    # Standard formats with labels
    r'(?:Date|Dated|Issued?|Invoice\s+Date|Document\s+Date)\s*[:]?\s*([0-9]{1,4}[-/\\ .][0-9]{1,2}[-/\\ .][0-9]{2,4})',
    r'(?:Date|Dated|Issued?|Invoice\s+Date|Document\s+Date)\s*[:]?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
    r'(?:Date|Dated|Issued?|Invoice\s+Date|Document\s+Date)\s*[:]?\s*(?:on\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+\d{4})',
    
    # Common date formats without labels (contextual)
    r'(?:^|\s)(\d{1,2}[-/\\ .]\d{1,2}[-/\\ .]\d{2,4})(?=\s|$)',
    r'(?:^|\s)(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})(?=\s|$)',
    r'(?:^|\s)(\d{4}[-/\\ .]\d{1,2}[-/\\ .]\d{1,2})(?=\s|$)',
    
    # Special formats
    r'(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4})',
    r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+\d{4})',
    r'(?:^|\s)(\d{1,2}[-/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/]\d{2,4})(?=\s|$)',
    r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+\d{4})',
    
    # ISO format and variations
    r'(\d{4}[-/\\ ]\d{2}[-/\\ ]\d{2})',
    r'(\d{8})'  # YYYYMMDD or DDMMYYYY or MMDDYYYY (handled by parse_date)
]

# Patterns specific to due dates
DUE_DATE_PATTERNS = [
    # Standard due date formats with labels
    r"(?:Due\s*Date|Payment\s*Due|Due\s*On|Payment Due Date|Due By)\s*[:]?\s*([0-9]{1,4}[/\-\. ][0-9]{1,2}[/\-\. ][0-9]{2,4})",
    r"(?:Due\s*Date|Payment\s*Due|Due\s*On|Payment Due Date|Due By)\s*[:]?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})",
    
    # Common due date formats without labels (contextual)
    r"(?:^|\s)(?:Due|Payable by|Pay by)\s+(\d{1,2}[/\-\. ]\d{1,2}[/\-\. ]\d{2,4})(?=\s|$)",
    r"(?:^|\s)(?:Due|Payable by|Pay by)\s+(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})(?=\s|$)",
    
    # Relative due dates (e.g., "Due in 30 days")
    r"(?:Due|Payment Due|Payable)\s+(?:in\s+)?(\d+)\s+days?\s+(?:from|after)?\s*(?:invoice|date)?",
    
    # Net terms (e.g., "Net 30")
    r"(?:Net|Terms)[\s:]+(\d+)[\s-]*(?:days?|d)"
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
def parse_date(date_str: str, reference_date: datetime = None, is_relative: bool = False) -> str:
    """
    Parse date string into ISO format (YYYY-MM-DD)
    
    Args:
        date_str: Date string in various formats
        reference_date: Reference date for relative date calculations
        is_relative: Whether this is a relative date (e.g., "30 days")
        
    Returns:
        ISO formatted date string or empty string if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return ""
    
    # Clean up the date string
    date_str = date_str.strip()
    
    # Handle relative dates (e.g., "30 days" from reference date)
    if is_relative and reference_date:
        try:
            days = int(date_str)
            result_date = reference_date + timedelta(days=days)
            return result_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return ""
    
    # Remove ordinal indicators (1st, 2nd, 3rd, 4th, etc.)
    date_str = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', date_str)
    
    # Try parsing with various date formats
    date_formats = [
        # Day-Month-Year with various separators
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %m %Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y", "%d %m %y",  # 2-digit year
        "%d %b %Y", "%d %B %Y",  # 01 Jan 2023, 01 January 2023
        "%d-%b-%Y", "%d-%B-%Y",  # 01-Jan-2023, 01-January-2023
        "%d %b, %Y", "%d %B, %Y",  # 01 Jan, 2023
        "%d %b %y", "%d %B %y",  # 01 Jan 23
        "%d-%b-%y", "%d-%B-%y",  # 01-Jan-23
        "%b %d, %Y", "%B %d, %Y",  # Jan 01, 2023
        "%b %d %Y", "%B %d %Y",  # Jan 01 2023
        "%b %d, %Y", "%B %d, %Y",  # Jan 01, 2023 (with comma)
        "%d %b %Y", "%d %B %Y",  # 01 Jan 2023 (no comma)
        
        # Month-Day-Year with various separators (US format)
        "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y", "%m %d %Y",
        "%m/%d/%y", "%m-%d-%y", "%m.%d.%y", "%m %d %y",  # 2-digit year
        "%b %d %Y", "%B %d %Y",  # Jan 01 2023
        "%b %d, %Y", "%B %d, %Y",  # Jan 01, 2023
        "%b-%d-%Y", "%B-%d-%Y",  # Jan-01-2023
        "%b %d, %y", "%B %d, %y",  # Jan 01, 23
        
        # Year-Month-Day (ISO format)
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y %m %d",
        "%y-%m-%d", "%y/%m/%d", "%y.%m.%d", "%y %m %d",  # 2-digit year
        
        # Special formats
        "%d%m%Y", "%d%m%y",  # DDMMYYYY, DDMMYY
        "%Y%m%d", "%y%m%d",  # YYYYMMDD, YYMMDD
        "%m%d%Y", "%m%d%y",  # MMDDYYYY, MMDDYY
    ]
    
    # Try parsing with each format
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            
            # Handle 2-digit years (pivot year: current year - 80 to current year + 20)
            if '%y' in fmt and not '%Y' in fmt:
                current_year = datetime.now().year
                current_century = (current_year // 100) * 100
                current_short_year = current_year % 100
                parsed_short_year = parsed_date.year % 100
                
                # Determine the century
                if parsed_short_year <= current_short_year + 20:
                    # If the parsed year is within 20 years after the current year, use current century
                    year = current_century + parsed_short_year
                else:
                    # Otherwise, use previous century
                    year = (current_century - 100) + parsed_short_year
                
                parsed_date = parsed_date.replace(year=year)
            
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Try to parse dates in the format YYYYMMDD, DDMMYYYY, or MMDDYYYY
    if re.match(r'^\d{8}$', date_str):
        # Try YYYYMMDD
        try:
            parsed_date = datetime.strptime(date_str, "%Y%m%d")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
        # Try DDMMYYYY
        try:
            parsed_date = datetime.strptime(date_str, "%d%m%Y")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
        # Try MMDDYYYY
        try:
            parsed_date = datetime.strptime(date_str, "%m%d%Y")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # If we have a reference date, try to handle relative dates (e.g., "30 days")
    if reference_date and date_str.isdigit():
        try:
            days = int(date_str)
            result_date = reference_date + timedelta(days=days)
            return result_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    
    # If all parsing attempts fail, return empty string
    return ""

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
    Extract date from text with support for various formats and relative dates
    
    Args:
        text: Text to search for date
        date_type: Type of date to extract ('issue' or 'due')
        
    Returns:
        Extracted date in ISO format or empty string if not found
    """
    if not text:
        return ""
    
    # First, try to find the issue date if we're looking for a due date
    issue_date = None
    if date_type == "due":
        issue_date_str = extract_date(text, date_type="issue")
        if issue_date_str:
            try:
                issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                pass
    
    # Get the appropriate patterns based on date type
    patterns = DATE_PATTERNS if date_type == "issue" else DUE_DATE_PATTERNS
    
    # Try each pattern to find a matching date
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if not match.groups():
                continue
                
            # Extract the matched date string
            date_str = match.group(1).strip()
            if not date_str:
                continue
            
            # Handle relative dates (e.g., "30 days")
            if date_type == "due" and any(term in match.group(0).lower() for term in ["net ", "terms", "days"]):
                # Extract the number of days
                days_match = re.search(r'\b(\d+)\s*(?:days?|d)\b', match.group(0), re.IGNORECASE)
                if days_match and issue_date:
                    days = int(days_match.group(1))
                    due_date = issue_date + timedelta(days=days)
                    return due_date.strftime("%Y-%m-%d")
            
            # Parse the date string
            parsed_date = parse_date(date_str, reference_date=issue_date, is_relative=False)
            if parsed_date:
                return parsed_date
    
    # If no date found and this is a due date, try to find relative dates without explicit patterns
    if date_type == "due" and issue_date:
        # Look for patterns like "Net 30" or "30 days"
        relative_patterns = [
            r'(?:net|terms?)[\s:]+(\d+)[\s-]*(?:days?|d)',
            r'(?:due in|payment due in|payable in)[\s:]+(\d+)[\s-]*(?:days?|d)',
            r'(\d+)[\s-]*(?:days?|d)[\s-]*(?:net|due|from date|from invoice)'
        ]
        
        for pattern in relative_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.group(1):
                try:
                    days = int(match.group(1))
                    due_date = issue_date + timedelta(days=days)
                    return due_date.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    continue
    
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


def normalize_description(description: str) -> str:
    """
    Normalize item description by removing common patterns and normalizing whitespace.
    
    Args:
        description: The raw description text
        
    Returns:
        Normalized description string
    """
    if not description:
        return ""
    
    # Remove any leading/trailing whitespace and normalize internal whitespace
    normalized = ' '.join(description.strip().split())
    
    # Remove common patterns that might appear in item descriptions
    patterns_to_remove = [
        r'\b\d+\s*(?:x|X)\s*\d+(?:\.\d+)?\b',  # Remove quantities like "2 x 1.5"
        r'\b\d+(?:\.\d+)?\s*[xX]\s*\$?\d+(?:\.\d+)?\b',  # Remove "2 x $10.00"
        r'\$?\d+(?:\.\d+)?\s*[xX]\s*\d+\b',  # Remove "$10.00 x 2"
        r'\b\d+(?:\.\d+)?\s*(?:pc|pcs|ea|each|unit)s?\b',  # Remove quantities like "2 pcs"
        r'\b\d+(?:\.\d+)?\s*\$?\d+(?:\.\d+)?\b',  # Remove numbers that look like prices
        r'\$\s*\d+(?:\.\d+)?',  # Remove standalone prices like "$100.00"
    ]
    
    for pattern in patterns_to_remove:
        normalized = re.sub(pattern, '', normalized)
    
    # Remove any remaining non-word characters from the start/end
    normalized = re.sub(r'^[^\w&]+|[^\w&]+$', '', normalized)
    
    return normalized.strip()

def extract_items(text: str) -> List[Dict[str, Any]]:
    """
    Extract line items from text with improved pattern matching and validation
    
    Args:
        text: Text to search for line items
        
    Returns:
        List of dictionaries with item details
    """
    items = []
    seen_items = set()  # Track seen items to avoid duplicates
    
    # Common patterns for false positives to exclude
    false_positive_patterns = [
        r'\b(?:IBAN|SWIFT|BIC|VAT|TAX|RTGS|NEFT|IFSC|SORT|ACCOUNT|ROUTING|BANK)[:\s]',
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card/IBAN numbers
        r'\b\d{2}[\s-]?[A-Z]{4}\s\d{4}\s\d{4}\s\d{4}\s\d{4}[\s-]?\d{2}\b',  # IBAN format
        r'\b(?:subtotal|total|tax|vat|balance|amount due|payment|terms|net|gross|discount|shipping|handling)\b',
    ]
    
    # More robust pattern that handles various invoice formats
    patterns = [
        # Pattern 1: Qty, Description, Unit Price, Total (tab/space separated)
        r'(?m)^\s*(?:\d+\.?\s*)?([^\n]{5,80}?)\s+(\d+(?:\.\d+)?)\s+([$€£¥]?\s*\d{1,3}(?:[,\s]?\d{3})*(?:\.\d{2})?)\s+([$€£¥]?\s*\d{1,3}(?:[,\s]?\d{3})*(?:\.\d{2})?)\s*$',
        # Pattern 2: Description, Qty, Unit Price, Total (with 'x' for quantity)
        r'(?m)^\s*(?:\d+\.?\s*)?([^\n]{5,80}?)\s+(\d+(?:\.\d+)?)\s*[xX]\s*([$€£¥]?\s*\d{1,3}(?:[,\s]?\d{3})*(?:\.\d{2})?)\s+([$€£¥]?\s*\d{1,3}(?:[,\s]?\d{3})*(?:\.\d{2})?)\s*$',
        # Pattern 3: Just Description and Total (common in simpler invoices)
        r'(?m)^\s*(?:\d+\.?\s*)?([^\n]{10,80}?)\s+([$€£¥]?\s*\d{1,3}(?:[,\s]?\d{3})*(?:\.\d{2})?)\s*$',
    ]
    
    # Clean up the text to improve matching
    cleaned_text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
    
    # Try each pattern and collect items
    for pattern in patterns:
        matches = re.finditer(pattern, cleaned_text)
        for match in matches:
            try:
                item = {}
                if len(match.groups()) >= 4:
                    # Pattern 1 or 2 with all fields
                    description = ' '.join(match.group(1).strip().split())
                    quantity = parse_float(match.group(2))
                    unit_price = parse_float(match.group(3).replace('$', '').replace('€', '').replace('£', '').replace('¥', '').replace(',', ''))
                    total_price = parse_float(match.group(4).replace('$', '').replace('€', '').replace('£', '').replace('¥', '').replace(',', ''))
                    
                    # If unit price is 0 but we have quantity and total, calculate it
                    if unit_price == 0 and quantity > 0 and total_price > 0:
                        unit_price = round(total_price / quantity, 2)
                        
                    item = {
                        "description": description,
                        "normalized_description": normalize_description(description),
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total_price": total_price
                    }
                elif len(match.groups()) == 2:
                    # Pattern 3 with just description and total
                    description = ' '.join(match.group(1).strip().split())
                    total_price = parse_float(match.group(2).replace('$', '').replace('€', '').replace('£', '').replace('¥', '').replace(',', ''))
                    
                    item = {
                        "description": description,
                        "normalized_description": normalize_description(description),
                        "quantity": 1.0,
                        "unit_price": total_price,
                        "total_price": total_price
                    }
                
                # Skip if no valid description or total
                if not item.get("description") or item.get("total_price", 0) <= 0:
                    continue
                    
                # Skip if description is too short or too long
                if len(item["description"]) < 5 or len(item["description"]) > 100:
                    continue
                    
                # Skip if description matches false positive patterns
                if any(re.search(pattern, item["description"], re.IGNORECASE) for pattern in false_positive_patterns):
                    continue
                    
                # Skip if this looks like a total/subtotal line or other non-item text
                if any(term in item["description"].lower() 
                     for term in ['subtotal', 'total', 'tax', 'vat', 'balance', 'amount due', 'payment', 'terms']):
                    continue
                
                # Create a unique identifier for this item to detect duplicates
                normalized_desc = item["normalized_description"].lower().strip()
                if not normalized_desc:  # If normalization removed everything, use original
                    normalized_desc = item["description"].lower().strip()
                
                item_id = (
                    normalized_desc,
                    round(float(item.get("unit_price", 0)), 2),
                    round(float(item.get("quantity", 1)), 2),
                    round(float(item.get("total_price", 0)), 2)
                )
                
                # Skip if we've seen this exact item before
                if item_id in seen_items:
                    continue
                seen_items.add(item_id)
                
                # Remove the normalized description before returning
                item.pop("normalized_description", None)
                
                # Add the item if it passes all validations
                items.append(item)
                        
            except (IndexError, ValueError, AttributeError) as e:
                logger.debug(f"Error parsing item: {e}")
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
    Extract payment terms from text with improved pattern matching
    
    Args:
        text: Text to search for payment terms
        
    Returns:
        Extracted payment terms or empty string if not found
"""
    if not text or not isinstance(text, str):
        return ""
    
    # Enhanced payment terms patterns
    payment_terms_patterns = [
        # Net 30, Net 15, etc.
        r'(?i)(?:payment\s*terms?|terms)[:\s]*(net\s+\d+\s+days?)',
        # Due on receipt, Due upon receipt
        r'(?i)(?:payment\s*terms?|terms)[:\s]*(due\s+(?:on|upon)\s+receipt)',
        # 2% 10 Net 30
        r'(?i)(\d+%\s+\d+\s+net\s+\d+)',
        # Common payment terms
        r'(?i)(?:payment\s*terms?|terms)[:\s]*(cash in advance|CIA|CWO|CASH WITH ORDER|CASH ON DELIVERY|COD|CASH ON DELIVERY|CASH IN ADVANCE|BANK TRANSFER|CREDIT CARD|PAYPAL|WIRE TRANSFER)',
        # Look for common payment terms in the document
        r'(?i)(?:payment\s*terms?|terms)[:\s]*([^\n]{10,100}?)(?=\n\n|\n\s*[A-Z]|\Z)',
        # Look for terms near currency symbols or payment-related words
        r'(?i)(?:payment|due|terms?)[^\n]{0,50}?\b(?:within|in|on|of)\b[^\n]{0,50}?\b(\d+\s*(?:days?|weeks?|months?)|\d+/\d+)\b',
        # Look for common payment term phrases
        r'(?i)\b(?:net|due)\s+(?:on\s+)?(?:receipt|invoice|delivery|\d+\s*(?:days?|weeks?|months?)|\d+/\d+)\b',
    ]
    
    # Try each pattern and return the first match
    for pattern in payment_terms_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            terms = match.group(1 if match.lastindex else 0).strip()
            # Clean up the extracted terms
            terms = re.sub(r'\s+', ' ', terms)  # Normalize whitespace
            terms = re.sub(r'^[^a-zA-Z0-9]+', '', terms)  # Remove leading non-alphanumeric
            terms = re.sub(r'[^a-zA-Z0-9\s%/-]+$', '', terms)  # Remove trailing non-alphanumeric
            return terms
    
    # If no specific terms found, try to find any mention of payment in the last few lines
    last_lines = '\n'.join(text.split('\n')[-10:])  # Look in the last 10 lines
    payment_keywords = ['payment', 'due', 'terms', 'net', 'days', 'upon', 'receipt', 'invoice']
    if any(keyword in last_lines.lower() for keyword in payment_keywords):
        # Try to extract the most relevant sentence
        sentences = re.split(r'(?<=[.!?])\s+', last_lines)
        for sentence in reversed(sentences):  # Check from bottom up
            if any(keyword in sentence.lower() for keyword in payment_keywords):
                return sentence.strip()
    
    return ""


def extract_notes(text: str) -> str:
    """
    Extract notes or additional information from text
    
    Args:
        text: Text to search for notes
        
    Returns:
        Extracted notes or empty string if not found
    """
    if not text or not isinstance(text, str):
        return ""
        
    for pattern in NOTES_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
            
    return ""


def extract_invoice_data(text: str) -> Dict[str, Any]:
    """
    Extract structured invoice data from text.
    
    Args:
        text: Raw text extracted from a PDF invoice
        
    Returns:
        Dictionary containing structured invoice data
    """
    if not text or not isinstance(text, str):
        return {}
    
    # Extract basic information
    document_number = extract_document_number(text)
    issue_date = extract_date(text, "issue")
    due_date = extract_date(text, "due")
    
    # Extract party information
    seller = extract_party(text, "seller")
    buyer = extract_party(text, "buyer")
    
    # Extract line items
    items = extract_items(text)
    
    # Extract totals
    totals = extract_totals(text)
    
    # Extract payment terms and notes
    payment_terms = extract_payment_terms(text)
    notes = extract_notes(text)
    
    # Compile the results
    invoice_data = {
        "document_number": document_number,
        "issue_date": issue_date,
        "due_date": due_date,
        "seller": seller,
        "buyer": buyer,
        "items": items,
        "totals": totals,
        "payment_terms": payment_terms,
        "notes": notes,
        "currency": totals.get("currency", ""),
        "language": "en"  # Default language, can be detected if needed
    }
    
    return invoice_data
