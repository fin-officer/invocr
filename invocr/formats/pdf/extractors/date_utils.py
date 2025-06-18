"""
Date extraction and parsing utilities.

This module contains functions for parsing and extracting dates from invoice text
in various formats.
"""

import re
from datetime import date, datetime, timedelta
from typing import Optional, Union

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.patterns import DATE_PATTERNS, DUE_DATE_PATTERNS

logger = get_logger(__name__)


def parse_date(
    date_str: str, reference_date: Optional[date] = None, is_relative: bool = False
) -> Optional[datetime]:
    """
    Parse a date string into a datetime object, handling various date formats.

    Args:
        date_str: The date string to parse
        reference_date: Reference date for relative dates (defaults to today)
        is_relative: If True, treat the input as a number of days relative to reference_date

    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not date_str:
        return None

    # Handle relative dates (e.g., "30 days")
    if is_relative and date_str.isdigit():
        days = int(date_str)
        ref_date = reference_date or datetime.now().date()
        if isinstance(ref_date, str):
            ref_date = datetime.strptime(ref_date, "%Y-%m-%d").date()
        result_date = ref_date + timedelta(days=days)
        return datetime.combine(result_date, datetime.min.time())

    # Strip any leading/trailing whitespace and special characters
    date_str = date_str.strip()
    date_str = re.sub(r'^[^\w\d]+|[^\w\d]+$', '', date_str)

    # Try different date formats
    formats = [
        # Common international formats
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%m-%d-%Y", "%m/%d/%Y", "%m.%d.%Y",
        
        # With 2-digit year
        "%d-%m-%y", "%d/%m/%y", "%d.%m.%y",
        "%y-%m-%d", "%y/%m/%d", "%y.%m.%d",
        "%m-%d-%y", "%m/%d/%y", "%m.%d.%y",
        
        # Date with month name
        "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
        "%d %b %y", "%d %B %y", "%b %d, %y", "%B %d, %y",
        "%d-%b-%Y", "%d-%B-%Y", "%b-%d-%Y", "%B-%d-%Y",
        
        # ISO-like formats
        "%Y%m%d", "%d%m%Y", "%m%d%Y",
        
        # Special formats with time
        "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S",
        "%d %b %Y %H:%M:%S", "%b %d, %Y %H:%M:%S",
    ]
    
    # Try each format
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            
            # Handle 2-digit years appropriately (assumes 1950-2049)
            if parsed_date.year < 100:
                if parsed_date.year < 50:
                    parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
                else:
                    parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
            
            return parsed_date
        except ValueError:
            continue
    
    # Try parsing dates with text month names in various languages
    try:
        # Handle English month names with ordinal day indicators
        ordinal_pattern = r'(\d+)(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})'
        match = re.search(ordinal_pattern, date_str, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month_num = month_map.get(month.lower()[:3])
            if month_num:
                return datetime(int(year), month_num, int(day))
    except (ValueError, AttributeError):
        pass
    
    # Handle special cases and common patterns
    try:
        # Special case: "DD Month YYYY"
        pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)[^\d]*(\d{4})'
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            day, month_name, year = match.groups()
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12,
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month = month_map.get(month_name.lower())
            if month:
                return datetime(int(year), month, int(day))
    except (ValueError, AttributeError):
        pass
    
    # Log failure
    logger.debug(f"Could not parse date string: {date_str}")
    return None


def extract_date(
    text: str,
    date_type: str = "issue",
    reference_date: Optional[Union[datetime, date, str]] = None
) -> Optional[datetime]:
    """
    Extract a date from text based on the specified date type (issue or due).

    Args:
        text: Text to search for dates
        date_type: Type of date to extract ('issue' or 'due')
        reference_date: Reference date (usually issue date) for relative date calculations

    Returns:
        Extracted date as datetime object or None if not found
    """
    if not text:
        return None

    # Get appropriate patterns based on date type
    if date_type.lower() == "due":
        primary_patterns = DUE_DATE_PATTERNS
        secondary_patterns = DATE_PATTERNS  # Fallback to general date patterns
    else:  # "issue" date or any other type defaults to issue date patterns
        primary_patterns = DATE_PATTERNS
        secondary_patterns = []
    
    # Try primary patterns first (specific to the date type)
    for pattern in primary_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            # If it's a relative date pattern (Net 30, etc.)
            if date_type.lower() == "due" and "net" in pattern.lower() or "terms" in pattern.lower():
                days = match.group(1)
                if days and days.isdigit():
                    return parse_date(days, reference_date, is_relative=True)
            
            # Regular date pattern
            date_str = match.group(1)
            if date_str:
                parsed_date = parse_date(date_str)
                if parsed_date:
                    return parsed_date
    
    # Try secondary patterns (general date patterns)
    for pattern in secondary_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            date_str = match.group(1)
            if date_str:
                parsed_date = parse_date(date_str)
                if parsed_date:
                    # For secondary patterns, verify it's reasonable
                    # (e.g., for due dates, should be after reference date)
                    if date_type.lower() == "due" and reference_date:
                        ref_date = reference_date
                        if isinstance(ref_date, str):
                            ref_date = datetime.strptime(ref_date, "%Y-%m-%d")
                        if parsed_date < ref_date:
                            continue  # Skip dates before reference date for due dates
                    return parsed_date
    
    # If still not found and it's a due date, check for common payment terms
    if date_type.lower() == "due":
        terms_patterns = [
            r"(?:net|terms|due\s+in)\s+(\d+)\s*(?:days?|d)",
            r"(\d+)\s+days?",
            r"net\s*(\d+)"
        ]
        
        for pattern in terms_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                days_str = match.group(1)
                if days_str and days_str.isdigit():
                    return parse_date(days_str, reference_date, is_relative=True)
    
    return None
