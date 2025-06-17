"""
Configuration package for PDF invoice extraction rules.

This package contains predefined extraction rules and patterns for
various invoice formats and fields.
"""

# Import rules from submodules to make them easily accessible
from .default_rules import DEFAULT_RULES, DATE_FORMATS, CURRENCY_SYMBOLS

__all__ = [
    'DEFAULT_RULES',
    'DATE_FORMATS',
    'CURRENCY_SYMBOLS'
]
