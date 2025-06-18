"""
Context-aware cross-field consistency checker for invoice data.

This module provides functionality to validate consistency between
different fields in extracted invoice data, ensuring logical relationships
are maintained.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from invocr.utils.logger import get_logger

logger = get_logger(__name__)


class ConsistencyChecker:
    """
    Validates consistency between related fields in extracted invoice data.
    
    This class implements various checks to ensure that extracted data
    maintains logical relationships between fields, such as:
    - Total amount = subtotal + tax amount
    - Line items sum up to subtotal
    - Issue date is before due date
    - Currency is consistent across monetary fields
    - Tax calculations are consistent with rates
    """
    
    def __init__(self, tolerance: float = 0.01):
        """
        Initialize the consistency checker.
        
        Args:
            tolerance: Tolerance for numerical comparisons (as a percentage)
        """
        self.logger = logger
        self.tolerance = tolerance
    
    def _parse_amount(self, amount: Any) -> Optional[Decimal]:
        """
        Parse an amount value to Decimal.
        
        Args:
            amount: Amount value to parse
            
        Returns:
            Parsed decimal amount or None if parsing fails
        """
        if amount is None:
            return None
            
        if isinstance(amount, (int, float)):
            return Decimal(str(amount))
            
        if isinstance(amount, Decimal):
            return amount
            
        if isinstance(amount, str):
            # Handle European format (1.234,56) vs US format (1,234.56)
            if ',' in amount and '.' in amount:
                # Check if it's European format (comma is decimal separator)
                if amount.rindex(',') > amount.rindex('.'):
                    # European format: replace dots with nothing, then comma with dot
                    clean_amount = amount.replace('.', '').replace(',', '.')
                else:
                    # US format: just remove commas
                    clean_amount = amount.replace(',', '')
            elif ',' in amount and '.' not in amount:
                # Could be European format with comma as decimal separator
                clean_amount = amount.replace(',', '.')
            else:
                # Standard format or no separators
                clean_amount = amount.replace(',', '')
                
            # Remove currency symbols and other non-numeric characters except decimal point and minus
            clean_amount = re.sub(r'[^\d.-]', '', clean_amount)
            
            try:
                return Decimal(clean_amount)
            except InvalidOperation:
                self.logger.warning(f"Could not parse amount: {amount}")
                return None
                
        return None
    
    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """
        Parse a date string to datetime.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if date_str is None:
            return None
            
        if isinstance(date_str, datetime):
            return date_str
            
        if isinstance(date_str, str):
            # Try common date formats
            formats = [
                '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y',
                '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d',
                '%d.%m.%Y', '%m.%d.%Y', '%Y.%m.%d',
                '%b %d %Y', '%d %b %Y', '%B %d %Y', '%d %B %Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                    
            self.logger.warning(f"Could not parse date: {date_str}")
            return None
            
        return None
    
    def _are_amounts_equal(self, amount1: Any, amount2: Any) -> bool:
        """
        Check if two amounts are equal within tolerance.
        
        Args:
            amount1: First amount
            amount2: Second amount
            
        Returns:
            True if amounts are equal within tolerance
        """
        dec1 = self._parse_amount(amount1)
        dec2 = self._parse_amount(amount2)
        
        if dec1 is None or dec2 is None:
            return False
            
        if dec1 == 0 and dec2 == 0:
            return True
            
        # Calculate relative difference
        max_abs = max(abs(dec1), abs(dec2))
        if max_abs == 0:
            return True
            
        relative_diff = abs(dec1 - dec2) / max_abs
        return relative_diff <= self.tolerance
    
    def check_total_consistency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check consistency between total amount, subtotal, and tax amount.
        
        Args:
            data: Extracted invoice data
            
        Returns:
            Dictionary with check results
        """
        result = {
            "check": "total_consistency",
            "valid": False,
            "details": {}
        }
        
        total = self._parse_amount(data.get("total_amount"))
        subtotal = self._parse_amount(data.get("subtotal"))
        tax = self._parse_amount(data.get("tax_amount"))
        
        result["details"]["parsed_total"] = str(total) if total is not None else None
        result["details"]["parsed_subtotal"] = str(subtotal) if subtotal is not None else None
        result["details"]["parsed_tax"] = str(tax) if tax is not None else None
        
        if total is None or subtotal is None:
            result["error"] = "Missing total or subtotal"
            return result
            
        # If tax is not specified, assume it's 0
        if tax is None:
            tax = Decimal('0')
            
        calculated_total = subtotal + tax
        result["details"]["calculated_total"] = str(calculated_total)
        
        if self._are_amounts_equal(total, calculated_total):
            result["valid"] = True
        else:
            result["error"] = f"Total amount inconsistency: {total} != {subtotal} + {tax}"
            
        return result
    
    def check_line_items_sum(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if line items sum up to the subtotal.
        
        Args:
            data: Extracted invoice data
            
        Returns:
            Dictionary with check results
        """
        result = {
            "check": "line_items_sum",
            "valid": False,
            "details": {}
        }
        
        subtotal = self._parse_amount(data.get("subtotal"))
        items = data.get("items", [])
        
        result["details"]["parsed_subtotal"] = str(subtotal) if subtotal is not None else None
        
        if subtotal is None:
            result["error"] = "Missing subtotal"
            return result
            
        if not items:
            result["error"] = "No line items found"
            return result
            
        # Calculate sum of line items
        item_sum = Decimal('0')
        item_amounts = []
        
        for item in items:
            amount = self._parse_amount(item.get("amount"))
            if amount is not None:
                item_sum += amount
                item_amounts.append(str(amount))
                
        result["details"]["item_amounts"] = item_amounts
        result["details"]["calculated_sum"] = str(item_sum)
        
        if self._are_amounts_equal(subtotal, item_sum):
            result["valid"] = True
        else:
            result["error"] = f"Line items sum inconsistency: {subtotal} != {item_sum}"
            
        return result
    
    def check_date_consistency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dates are logically consistent.
        
        Args:
            data: Extracted invoice data
            
        Returns:
            Dictionary with check results
        """
        result = {
            "check": "date_consistency",
            "valid": True,
            "details": {}
        }
        
        issue_date = self._parse_date(data.get("issue_date"))
        due_date = self._parse_date(data.get("due_date"))
        
        result["details"]["parsed_issue_date"] = issue_date.isoformat() if issue_date else None
        result["details"]["parsed_due_date"] = due_date.isoformat() if due_date else None
        
        if issue_date is None or due_date is None:
            # If either date is missing, we can't check consistency
            result["valid"] = True
            result["details"]["note"] = "One or both dates missing, skipping check"
            return result
            
        # Check if issue date is before or equal to due date
        if issue_date > due_date:
            result["valid"] = False
            result["error"] = f"Issue date ({issue_date.isoformat()}) is after due date ({due_date.isoformat()})"
            
        # Check if due date is not too far in the future (more than 1 year)
        if due_date > issue_date + timedelta(days=365):
            result["valid"] = False
            result["error"] = "Due date is more than 1 year after issue date"
            
        return result
    
    def check_currency_consistency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if currency is consistent across monetary fields.
        
        Args:
            data: Extracted invoice data
            
        Returns:
            Dictionary with check results
        """
        result = {
            "check": "currency_consistency",
            "valid": True,
            "details": {}
        }
        
        # Extract currency code
        currency = data.get("currency")
        if not currency:
            result["valid"] = True
            result["details"]["note"] = "No currency specified, skipping check"
            return result
            
        result["details"]["currency"] = currency
        
        # Check currency symbols in monetary fields
        monetary_fields = ["total_amount", "subtotal", "tax_amount"]
        inconsistent_fields = []
        
        for field in monetary_fields:
            value = data.get(field)
            if not isinstance(value, str):
                continue
                
            # Check for currency symbols that don't match the specified currency
            if currency == "USD" and "$" not in value and "USD" not in value:
                inconsistent_fields.append(field)
            elif currency == "EUR" and "€" not in value and "EUR" not in value:
                inconsistent_fields.append(field)
            elif currency == "GBP" and "£" not in value and "GBP" not in value:
                inconsistent_fields.append(field)
                
        # Check line items
        items = data.get("items", [])
        for i, item in enumerate(items):
            amount = item.get("amount")
            if not isinstance(amount, str):
                continue
                
            if currency == "USD" and "$" not in amount and "USD" not in amount:
                inconsistent_fields.append(f"items[{i}].amount")
            elif currency == "EUR" and "€" not in amount and "EUR" not in amount:
                inconsistent_fields.append(f"items[{i}].amount")
            elif currency == "GBP" and "£" not in amount and "GBP" not in amount:
                inconsistent_fields.append(f"items[{i}].amount")
                
        if inconsistent_fields:
            result["valid"] = False
            result["error"] = f"Currency inconsistency in fields: {', '.join(inconsistent_fields)}"
            result["details"]["inconsistent_fields"] = inconsistent_fields
            
        return result
    
    def check_tax_calculation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if tax calculations are consistent.
        
        Args:
            data: Extracted invoice data
            
        Returns:
            Dictionary with check results
        """
        result = {
            "check": "tax_calculation",
            "valid": False,
            "details": {}
        }
        
        subtotal = self._parse_amount(data.get("subtotal"))
        tax = self._parse_amount(data.get("tax_amount"))
        tax_rate = data.get("tax_rate")
        
        result["details"]["parsed_subtotal"] = str(subtotal) if subtotal is not None else None
        result["details"]["parsed_tax"] = str(tax) if tax is not None else None
        result["details"]["tax_rate"] = tax_rate
        
        if subtotal is None or tax is None:
            result["error"] = "Missing subtotal or tax amount"
            return result
            
        # If tax rate is specified, check if tax amount matches calculation
        if tax_rate is not None:
            try:
                # Parse tax rate (remove % symbol if present)
                if isinstance(tax_rate, str):
                    tax_rate = tax_rate.strip().rstrip('%')
                    
                rate = Decimal(str(tax_rate)) / Decimal('100')
                calculated_tax = subtotal * rate
                
                result["details"]["parsed_rate"] = str(rate)
                result["details"]["calculated_tax"] = str(calculated_tax)
                
                if self._are_amounts_equal(tax, calculated_tax):
                    result["valid"] = True
                else:
                    result["error"] = f"Tax calculation inconsistency: {tax} != {subtotal} * {rate}"
            except (InvalidOperation, TypeError):
                result["error"] = f"Could not parse tax rate: {tax_rate}"
        else:
            # If no tax rate is specified, check if tax is reasonable (e.g., not more than 30% of subtotal)
            if subtotal > 0 and tax >= 0:
                tax_percentage = (tax / subtotal) * 100
                result["details"]["calculated_tax_percentage"] = str(tax_percentage)
                
                if tax_percentage <= 30:
                    result["valid"] = True
                else:
                    result["error"] = f"Tax amount seems too high: {tax_percentage}% of subtotal"
            else:
                result["valid"] = True  # Can't check reasonableness with zero or negative values
                
        return result
    
    def check_all(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all consistency checks on the extracted data.
        
        Args:
            data: Extracted invoice data
            
        Returns:
            Dictionary with all check results
        """
        results = {
            "overall_valid": True,
            "checks": {}
        }
        
        # Run all checks
        checks = [
            self.check_total_consistency,
            self.check_line_items_sum,
            self.check_date_consistency,
            self.check_currency_consistency,
            self.check_tax_calculation
        ]
        
        for check_func in checks:
            check_name = check_func.__name__.replace("check_", "")
            check_result = check_func(data)
            results["checks"][check_name] = check_result
            
            # Update overall validity
            if not check_result["valid"]:
                results["overall_valid"] = False
                
        return results
