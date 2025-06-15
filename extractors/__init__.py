"""
Extractor modules for invoice data extraction.

This package contains the base extractor class and language-specific extractors.
"""

from .base import DataExtractor  # noqa: F401

# Language-specific extractors will be imported here
from .en.extractor import EnglishExtractor  # noqa: F401
from .pl.extractor import PolishExtractor  # noqa: F401
from .de.extractor import GermanExtractor  # noqa: F401

__all__ = ['DataExtractor', 'EnglishExtractor', 'PolishExtractor', 'GermanExtractor']
