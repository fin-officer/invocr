"""
Numeric extraction and parsing utilities.

This module contains functions for parsing and extracting numeric values from invoice text,
including amounts, quantities, and other numeric fields.
"""

import re
from typing import Optional

from invocr.utils.logger import get_logger

logger = get_logger(__name__)


def parse_float(value_str: str) -> float:
    """
    Parse string into float, handling various formats.

    Args:
        value_str: String representing a number

    Returns:
        Float value or 0.0 if parsing fails
    """
    if not value_str:
        return 0.0
    
    # Remove currency symbols and any non-numeric characters except decimal and negative
    value_str = re.sub(r'[^\d\-.,]', '', str(value_str))
    
    # Handle European-style numbers (comma as decimal separator)
    if ',' in value_str and '.' in value_str:
        # If both comma and period exist, the last one is the decimal separator
        if value_str.rindex(',') > value_str.rindex('.'):
            value_str = value_str.replace('.', '')  # Remove thousand separators
            value_str = value_str.replace(',', '.')  # Convert decimal separator
        else:
            value_str = value_str.replace(',', '')  # Remove thousand separators
    elif ',' in value_str and '.' not in value_str:
        # If only comma exists, treat it as decimal separator
        value_str = value_str.replace(',', '.')
    
    # Final cleanup - remove any remaining invalid characters
    value_str = re.sub(r'[^\d\-.]', '', value_str)
    
    try:
        return float(value_str)
    except (ValueError, TypeError):
        logger.debug(f"Could not convert to float: {value_str}")
        return 0.0


def extract_numeric_value(text: str, pattern: str) -> float:
    """
    Extract numeric value from text using the given pattern.
    
    Args:
        text: The text to search in
        pattern: Regex pattern with a single group for the value
        
    Returns:
        Extracted float value or 0.0 if not found
    """
    if not text or not pattern:
        return 0.0
        
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        value_str = match.group(1)
        return parse_float(value_str)
    
    return 0.0


def extract_currency(text: str) -> str:
    """
    Extract currency symbol or code from text.
    
    Args:
        text: Text to search for currency indicators
        
    Returns:
        Currency code (USD, EUR, etc.) or empty string if not found
    """
    # Check for explicit currency declarations
    currency_patterns = [
        r"(?i)currency\s*[:]?\s*([A-Z]{3})",
        r"(?i)amount in ([A-Z]{3})",
        r"(?i)total [^$€£]* in ([A-Z]{3})",
    ]
    
    for pattern in currency_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).upper()
    
    # Check for currency symbols and map to codes
    symbol_map = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "₽": "RUB",
        "zł": "PLN",
        "kr": "SEK",  # Could also be DKK, NOK depending on context
    }
    
    for symbol, code in symbol_map.items():
        if symbol in text:
            # For $, confirm it's likely USD not CAD or AUD
            if symbol == "$" and ("USD" in text or "US dollar" in text.lower() or "United States" in text):
                return "USD"
            elif symbol == "$" and "CAD" in text:
                return "CAD"
            elif symbol == "$" and "AUD" in text:
                return "AUD"
            elif symbol == "kr" and "SEK" in text:
                return "SEK"
            elif symbol == "kr" and "NOK" in text:
                return "NOK"
            elif symbol == "kr" and "DKK" in text:
                return "DKK"
            else:
                return code
    
    # If all else fails, look for three-letter currency codes
    code_pattern = r"\b(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|PLN|DKK|NOK|SEK)\b"
    match = re.search(code_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return ""  # No currency found
