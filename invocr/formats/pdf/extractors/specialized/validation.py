"""
Validation module for extracted data.

This module provides validation rules and utilities for ensuring that extracted data
meets expected formats, ranges, and business rules.
"""

import re
from typing import Any, Dict, List, Optional, Union, Callable
from decimal import Decimal, InvalidOperation
from datetime import datetime
import logging

from invocr.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationRules:
    """
    Collection of validation rules for different data types.
    
    This class provides static methods for validating different types of data
    commonly found in invoices and other financial documents.
    """
    
    @staticmethod
    def validate_percentage(value: Union[str, float, int, Decimal]) -> bool:
        """
        Validate that a value is a valid percentage (0-100).
        
        Args:
            value: The value to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if isinstance(value, str):
                # Remove % sign if present
                value = value.replace('%', '').strip()
                value = Decimal(value)
            elif isinstance(value, (int, float)):
                value = Decimal(str(value))
            
            # Check range
            return Decimal('0') <= value <= Decimal('100')
        except (InvalidOperation, ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_currency_amount(value: Union[str, float, int, Decimal]) -> bool:
        """
        Validate that a value is a valid currency amount.
        
        Args:
            value: The value to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if isinstance(value, str):
                # Remove currency symbols and spaces
                value = re.sub(r'[^\d.,\-+]', '', value).strip()
                value = Decimal(value)
            elif isinstance(value, (int, float)):
                value = Decimal(str(value))
            
            # Check precision (max 4 decimal places)
            decimal_places = abs(value.as_tuple().exponent)
            return decimal_places <= 4
        except (InvalidOperation, ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_date(value: Union[str, datetime]) -> bool:
        """
        Validate that a value is a valid date.
        
        Args:
            value: The value to validate
            
        Returns:
            True if valid, False otherwise
        """
        if isinstance(value, datetime):
            return True
        
        if not isinstance(value, str):
            return False
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y',
            '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
            '%Y.%m.%d', '%d.%m.%Y', '%m.%d.%Y',
            '%d %b %Y', '%d %B %Y'
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        
        return False
    
    @staticmethod
    def validate_tax_id(value: str, country_code: Optional[str] = None) -> bool:
        """
        Validate that a value is a valid tax ID for the given country.
        
        Args:
            value: The tax ID to validate
            country_code: Optional country code for country-specific validation
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(value, str):
            return False
        
        # Remove spaces and special characters
        value = re.sub(r'[^A-Z0-9]', '', value.upper())
        
        # Country-specific validation
        if country_code:
            if country_code.upper() == 'PL':
                # Polish NIP (10 digits)
                return bool(re.match(r'^[0-9]{10}$', value))
            elif country_code.upper() == 'DE':
                # German tax ID (11 digits)
                return bool(re.match(r'^[0-9]{11}$', value))
            elif country_code.upper() == 'FR':
                # French SIRET (14 digits)
                return bool(re.match(r'^[0-9]{14}$', value))
        
        # Generic validation (at least 5 alphanumeric characters)
        return len(value) >= 5 and bool(re.match(r'^[A-Z0-9]+$', value))
    
    @staticmethod
    def validate_phone_number(value: str) -> bool:
        """
        Validate that a value is a valid phone number.
        
        Args:
            value: The phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(value, str):
            return False
        
        # Remove spaces, dashes, parentheses
        value = re.sub(r'[\s\-\(\)]', '', value)
        
        # Check for international format or local format
        return bool(re.match(r'^\+?[0-9]{8,15}$', value))
    
    @staticmethod
    def validate_email(value: str) -> bool:
        """
        Validate that a value is a valid email address.
        
        Args:
            value: The email to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(value, str):
            return False
        
        # Simple email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))


class DataValidator:
    """
    Validator for extracted document data.
    
    This class provides methods for validating extracted data against
    business rules and formatting requirements.
    """
    
    def __init__(self):
        """Initialize the data validator."""
        self.logger = logger
        self.validation_rules = {
            'percentage': ValidationRules.validate_percentage,
            'currency': ValidationRules.validate_currency_amount,
            'date': ValidationRules.validate_date,
            'tax_id': ValidationRules.validate_tax_id,
            'phone': ValidationRules.validate_phone_number,
            'email': ValidationRules.validate_email
        }
    
    def validate_field(self, field_name: str, value: Any, field_type: str) -> Dict[str, Any]:
        """
        Validate a single field based on its type.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            field_type: Type of validation to apply
            
        Returns:
            Dictionary with validation results
        """
        if field_type not in self.validation_rules:
            self.logger.warning(f"Unknown field type '{field_type}' for field '{field_name}'")
            return {
                'field': field_name,
                'value': value,
                'valid': False,
                'error': f"Unknown field type: {field_type}"
            }
        
        validation_func = self.validation_rules[field_type]
        is_valid = validation_func(value)
        
        result = {
            'field': field_name,
            'value': value,
            'valid': is_valid
        }
        
        if not is_valid:
            result['error'] = f"Invalid {field_type} format"
        
        return result
    
    def validate_document_data(self, data: Dict[str, Any], field_types: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate multiple fields in a document.
        
        Args:
            data: Dictionary of field values
            field_types: Dictionary mapping field names to their types
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'fields': {}
        }
        
        for field_name, field_type in field_types.items():
            if field_name in data:
                field_result = self.validate_field(field_name, data[field_name], field_type)
                results['fields'][field_name] = field_result
                
                if not field_result['valid']:
                    results['valid'] = False
        
        return results
    
    def validate_totals_consistency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that totals are consistent with line items.
        
        Args:
            data: Document data with line items and totals
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': []
        }
        
        # Check if we have line items and totals
        if 'line_items' not in data or not data['line_items']:
            results['valid'] = False
            results['errors'].append("No line items found")
            return results
        
        try:
            # Calculate total from line items
            calculated_total = Decimal('0')
            for item in data['line_items']:
                if 'amount' in item and item['amount']:
                    amount = item['amount']
                    if isinstance(amount, str):
                        amount = Decimal(re.sub(r'[^\d.,\-]', '', amount))
                    calculated_total += Decimal(str(amount))
            
            # Compare with document total
            if 'total_amount' in data and data['total_amount']:
                doc_total = data['total_amount']
                if isinstance(doc_total, str):
                    doc_total = Decimal(re.sub(r'[^\d.,\-]', '', doc_total))
                else:
                    doc_total = Decimal(str(doc_total))
                
                # Allow for small rounding differences (0.02)
                if abs(calculated_total - doc_total) > Decimal('0.02'):
                    results['valid'] = False
                    results['errors'].append(
                        f"Total amount mismatch: document states {doc_total}, calculated {calculated_total}"
                    )
        except (InvalidOperation, ValueError, TypeError) as e:
            results['valid'] = False
            results['errors'].append(f"Error validating totals: {str(e)}")
        
        return results
    
    def register_custom_validator(self, field_type: str, validator_func: Callable) -> None:
        """
        Register a custom validation function.
        
        Args:
            field_type: Type name for the validator
            validator_func: Validation function that returns True/False
        """
        if field_type in self.validation_rules:
            self.logger.warning(f"Overriding existing validator for '{field_type}'")
        
        self.validation_rules[field_type] = validator_func
        self.logger.info(f"Registered custom validator for '{field_type}'")
