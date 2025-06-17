"""
Configuration package for PDF invoice extraction rules.

This package contains predefined extraction rules and patterns for
various invoice formats and fields.
"""

# Import rules from the fixed rules module
from .default_rules_fixed import (  # noqa: F401
    CURRENCY_SYMBOLS,
    DATE_FORMATS,
    DEFAULT_RULES,
    get_currency_symbols,
    get_date_formats,
    get_default_rules,
)

__all__ = [
    "DEFAULT_RULES",
    "DATE_FORMATS",
    "CURRENCY_SYMBOLS",
    "get_default_rules",
    "get_currency_symbols",
    "get_date_formats",
]
