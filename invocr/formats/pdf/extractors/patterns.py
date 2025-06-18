"""
Common regex patterns for PDF data extraction.

This module contains centralized regex patterns for extracting various data elements from PDF text.
"""

# Regular expression patterns for various data elements
DOCUMENT_NUMBER_PATTERNS = [
    r"Invoice\s+Number\s*[:#]?\s*([A-Z0-9-]+)",
    r"(?:Invoice|Bill|Receipt)\s*[#:]?\s*([A-Z0-9-]+)",
    r"(?:No\.?|Number|Nr\.?)\s*[:#]?\s*([A-Z0-9-]+)",
]

# Common date patterns for invoice dates (case-insensitive matching)
DATE_PATTERNS = [
    # Standard formats with labels (most specific first)
    r"(?i)(?:Date|Dated|Issued?|Invoice\s+Date|Document\s+Date|Date\s+of\s+Issue|Issued?\s+on?)\s*[:]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]*\d{4})",
    r"(?i)(?:Date|Dated|Issued?|Invoice\s+Date|Document\s+Date|Date\s+of\s+Issue|Issued?\s+on?)\s*[:]?\s*(\d{1,2}[-/\\ .]\d{1,2}[-/\\ .]\d{2,4})",
    r"(?i)(?:Date|Dated|Issued?|Invoice\s+Date|Document\s+Date|Date\s+of\s+Issue|Issued?\s+on?)\s*[:]?\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,2}(?:st|nd|rd|th)?[\s,]+\d{4})",
    # Common date formats without labels (contextual)
    r"(?<![\d-])(\d{1,2}[-/\\ .]\d{1,2}[-/\\ .]\d{2,4})(?![\d-])",  # DD-MM-YYYY or MM/DD/YYYY
    r"(?<![\d-])(\d{4}[-/\\ .]\d{1,2}[-/\\ .]\d{1,2})(?![\d-])",  # YYYY-MM-DD
    r"(?i)(?<![\d-])(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]*\d{4})(?![\d-])",
    r"(?i)(?<![\d-])((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,2}(?:st|nd|rd|th)?[\s,]+\d{4})(?![\d-])",
    # Special formats with month names
    r"(?i)(\d{1,2}[-/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/]\d{2,4})",
    r"(?i)(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+\d{4})",
    r"(?i)(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]*\d{4})",
    # ISO format and variations (with word boundaries)
    r"\b(\d{4}[-/\\ ]\d{2}[-/\\ ]\d{2})\b",
    r"\b(\d{2}[-/\\ ]\d{2}[-/\\ ]\d{2})\b",  # YY-MM-DD or DD-MM-YY
    r"\b(\d{8})\b",  # YYYYMMDD or DDMMYYYY or MMDDYYYY
]

# Patterns specific to due dates (case-insensitive matching)
DUE_DATE_PATTERNS = [
    # Standard due date formats with labels (most specific first)
    r"(?i)(?:Due\s*Date|Payment\s*Due|Due\s*On|Payment\s+Due\s+Date|Due\s+By|Payment\s+Date|Payment\s+Due\s+On)\s*[:]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]*\d{4})",
    r"(?i)(?:Due\s*Date|Payment\s*Due|Due\s*On|Payment\s+Due\s+Date|Due\s+By|Payment\s+Date|Payment\s+Due\s+On)\s*[:]?\s*(\d{1,2}[-/\\ .]\d{1,2}[-/\\ .]\d{2,4})",
    # Due date with label and numeric dates
    r"(?:due|payment\s*date|date\s*due|payment\s*due\s*date)[\s:]+(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})",
    # Relative due dates (Net 30, Due in 30 days, etc.)
    r"(?:net|terms?|due\s+in)\s+(\d+)\s*(?:days?|d|day\s+after|day\s+from|days\s+after|days\s+from)?",
]

# Item line patterns for different invoice formats
ITEM_PATTERNS = [
    # Format: Description Quantity Unit Price Amount
    r"(?P<description>[\w\s\-.,()&+'/]+?)\s+(?P<quantity>\d+(?:[.,]\d+)?)\s+(?P<unit>(?:[a-zA-Z]+|pcs|pc|ea))\s+(?P<unit_price>\d+(?:[.,]\d+)?)\s+(?P<total>\d+(?:[.,]\d+)?)",
    
    # Format: Quantity x Description @ Unit Price Amount
    r"(?P<quantity>\d+(?:[.,]\d+)?)\s*(?:x|×)\s*(?P<description>[\w\s\-.,()&+'/]+?)\s*@\s*(?P<unit_price>\d+(?:[.,]\d+)?)\s+(?P<total>\d+(?:[.,]\d+)?)",
    
    # Format: Quantity Description Unit Price Amount
    r"(?P<quantity>\d+(?:[.,]\d+)?)\s+(?P<description>[\w\s\-.,()&+'/]+?)\s+(?P<unit_price>\d+(?:[.,]\d+)?)\s+(?P<total>\d+(?:[.,]\d+)?)",
    
    # Format: Description - Amount
    r"(?P<description>[\w\s\-.,()&+'/]+?)\s*-\s*(?P<total>\d+(?:[.,]\d+)?)"
]

# Patterns for finding total amount
TOTAL_AMOUNT_PATTERNS = [
    r"(?i)(?:total|grand\s+total|amount\s+due)[^$€£\d]{1,100}([€$£]?\s*\d+(?:[,.]\d+)?)",
    r"(?i)(?:total|grand\s+total|amount\s+due|to\s+pay)[^\d]{0,10}([€$£]?\s*\d+(?:[,.]\d+)?)",
    r"(?i)(?:total\s+amount|amount\s+total)(?:[^\d]{0,20})([€$£]?\s*\d+(?:[,.]\d+)?)",
    r"(?i)(?:sum\s+total|total\s+sum)[^\d]{0,10}([€$£]?\s*\d+(?:[,.]\d+)?)",
    r"(?i)(?:balance\s+due|due\s+amount|amount\s+now\s+due)[^\d]{0,10}([€$£]?\s*\d+(?:[,.]\d+)?)",
]

# Patterns for finding subtotal amount
SUBTOTAL_PATTERNS = [
    r"(?i)(?:subtotal|sub-total|net\s+amount)[^$€£\d]{1,100}([€$£]?\s*\d+(?:[,.]\d+)?)",
    r"(?i)(?:subtotal|sub-total|net)[^\d]{0,10}([€$£]?\s*\d+(?:[,.]\d+)?)",
    r"(?i)(?:net\s+total)[^\d]{0,10}([€$£]?\s*\d+(?:[,.]\d+)?)",
]

# Patterns for finding tax amount
TAX_AMOUNT_PATTERNS = [
    r"(?i)(?:tax|vat|gst|sales\s+tax)[^$€£\d]{1,100}([€$£]?\s*\d+(?:[,.]\d+)?)",
    r"(?i)(?:tax|vat|gst|sales\s+tax)[^\d]{0,10}([€$£]?\s*\d+(?:[,.]\d+)?)",
    r"(?i)(?:tax\s+amount|vat\s+amount)[^\d]{0,10}([€$£]?\s*\d+(?:[,.]\d+)?)",
]

# Patterns for finding tax rate
TAX_RATE_PATTERNS = [
    r"(?i)(?:tax|vat|gst)\s*(?:rate)?:?\s*(\d+(?:[,.]\d+)?)\s*%",
    r"(\d+(?:[,.]\d+)?)\s*%\s*(?:tax|vat|gst)",
]

# Patterns for finding currency
CURRENCY_PATTERNS = [
    r"(?i)currency:?\s*([A-Z]{3})",
    r"(?i)(?:amount|total)[^\n]*?([€$£]|EUR|USD|GBP|PLN)",
]

# Patterns for extracting payment terms
PAYMENT_TERMS_PATTERNS = [
    r"(?i)(?:payment\s+terms|terms\s+of\s+payment|payment\s+condition)(?:s)?:?\s*(.+?)(?:\n|$)",
    r"(?i)(?:terms|payment):?\s*(.+?)(?:\n|$)",
    r"(?i)(?:due|payment)\s+(?:within|in)\s+(\d+)\s+days",
    r"(?i)(?:net|payment\s+due)\s+(\d+)",
]

# Patterns for extracting notes or additional information
NOTES_PATTERNS = [
    r"(?i)(?:notes?|comment|remark|additional\s+information):?\s*(.+?)(?:\n\n|$)",
]
