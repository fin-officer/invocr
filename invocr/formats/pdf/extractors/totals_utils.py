"""
Totals extraction utilities.

This module contains functions for extracting invoice totals, including
subtotals, tax amounts, and total amounts from invoice text.
"""

import re
from typing import Dict, Any, List, Optional

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.patterns import (
    TOTAL_AMOUNT_PATTERNS,
    SUBTOTAL_PATTERNS,
    TAX_AMOUNT_PATTERNS,
    TAX_RATE_PATTERNS,
    CURRENCY_PATTERNS
)
from invocr.formats.pdf.extractors.numeric_utils import parse_float, extract_currency

logger = get_logger(__name__)


def extract_totals(text: str) -> Dict[str, Any]:
    """
    Extract totals from invoice text.

    Args:
        text: Text to search for totals

    Returns:
        Dictionary with total amounts
    """
    result = {
        "total_amount": 0.0,
        "subtotal": 0.0,
        "tax_amount": 0.0,
        "tax_rate": 0.0,
        "currency": ""
    }
    
    if not text:
        return result
    
    # Extract currency first
    result["currency"] = extract_currency(text)
    
    # Extract total amount
    for pattern in TOTAL_AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value_str = match.group(1)
            result["total_amount"] = parse_float(value_str)
            break
    
    # Extract subtotal
    for pattern in SUBTOTAL_PATTERNS:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value_str = match.group(1)
            result["subtotal"] = parse_float(value_str)
            break
    
    # Extract tax amount
    for pattern in TAX_AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value_str = match.group(1)
            result["tax_amount"] = parse_float(value_str)
            break
    
    # Extract tax rate
    for pattern in TAX_RATE_PATTERNS:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value_str = match.group(1)
            result["tax_rate"] = parse_float(value_str)
            break
    
    # Calculate missing values if possible
    if result["subtotal"] > 0 and result["tax_amount"] > 0 and result["total_amount"] == 0:
        result["total_amount"] = result["subtotal"] + result["tax_amount"]
    
    if result["subtotal"] > 0 and result["tax_amount"] == 0 and result["total_amount"] > 0:
        result["tax_amount"] = result["total_amount"] - result["subtotal"]
    
    if result["subtotal"] == 0 and result["tax_amount"] > 0 and result["total_amount"] > 0:
        result["subtotal"] = result["total_amount"] - result["tax_amount"]
    
    # Calculate tax rate if missing
    if result["tax_rate"] == 0 and result["subtotal"] > 0 and result["tax_amount"] > 0:
        result["tax_rate"] = (result["tax_amount"] / result["subtotal"]) * 100
    
    return result


def calculate_totals_from_items(items: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate totals from a list of invoice items.
    
    Args:
        items: List of item dictionaries
        
    Returns:
        Dictionary with calculated totals
    """
    result = {
        "subtotal": 0.0,
        "total_amount": 0.0,
        "tax_amount": 0.0
    }
    
    if not items:
        return result
    
    # Sum up item amounts
    for item in items:
        if "amount" in item and item["amount"]:
            result["subtotal"] += float(item["amount"])
        elif "total" in item and item["total"]:
            result["subtotal"] += float(item["total"])
        elif "unit_price" in item and "quantity" in item:
            amount = float(item["unit_price"]) * float(item["quantity"])
            result["subtotal"] += amount
    
    # If there are tax fields in items, sum those up too
    tax_amount = 0.0
    for item in items:
        if "tax_amount" in item and item["tax_amount"]:
            tax_amount += float(item["tax_amount"])
    
    if tax_amount > 0:
        result["tax_amount"] = tax_amount
    
    # Calculate total
    result["total_amount"] = result["subtotal"] + result["tax_amount"]
    
    return result


def validate_totals(extracted_totals: Dict[str, Any], calculated_totals: Dict[str, float]) -> Dict[str, Any]:
    """
    Validate and reconcile extracted totals with calculated totals from items.
    
    Args:
        extracted_totals: Totals extracted from the document text
        calculated_totals: Totals calculated from the line items
        
    Returns:
        Validated and reconciled totals
    """
    result = extracted_totals.copy()
    
    # If extracted subtotal is 0 or invalid, use calculated
    if result["subtotal"] <= 0 and calculated_totals["subtotal"] > 0:
        result["subtotal"] = calculated_totals["subtotal"]
    
    # If extracted total is 0 or invalid, use calculated
    if result["total_amount"] <= 0 and calculated_totals["total_amount"] > 0:
        result["total_amount"] = calculated_totals["total_amount"]
    
    # Check for consistency between extracted and calculated
    subtotal_diff = abs(result["subtotal"] - calculated_totals["subtotal"])
    total_diff = abs(result["total_amount"] - calculated_totals["total_amount"])
    
    # If significant differences, log and potentially adjust
    if result["subtotal"] > 0 and calculated_totals["subtotal"] > 0:
        subtotal_percent_diff = subtotal_diff / max(result["subtotal"], calculated_totals["subtotal"]) * 100
        if subtotal_percent_diff > 5:  # More than 5% difference
            logger.warning(f"Subtotal inconsistency: extracted={result['subtotal']}, calculated={calculated_totals['subtotal']}")
    
    if result["total_amount"] > 0 and calculated_totals["total_amount"] > 0:
        total_percent_diff = total_diff / max(result["total_amount"], calculated_totals["total_amount"]) * 100
        if total_percent_diff > 5:  # More than 5% difference
            logger.warning(f"Total amount inconsistency: extracted={result['total_amount']}, calculated={calculated_totals['total_amount']}")
    
    return result
