"""
Configuration package for PDF invoice extraction rules.

This package contains predefined extraction rules and patterns for
various invoice formats and fields.
"""

# Import rules from the fixed rules module
from .default_rules_fixed import (
    DEFAULT_RULES, 
    DATE_FORMATS, 
    CURRENCY_SYMBOLS,
    get_default_rules,
    get_currency_symbols,
    get_date_formats
) # noqa: F401

__all__ = [
    'DEFAULT_RULES',
    'DATE_FORMATS',
    'CURRENCY_SYMBOLS',
    'get_default_rules',
    'get_currency_symbols',
    'get_date_formats'
]
