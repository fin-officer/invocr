"""
Language-specific extractors for processing documents in different languages.

This package contains extractor implementations for various languages, each capable
of processing text and extracting structured data in a language-specific way.

Available language extractors:
- English (en): EnglishExtractor
- German (de): GermanExtractor
- Spanish (es): SpanishExtractor
- French (fr): FrenchExtractor
- Polish (pl): PolishExtractor

Each language module provides an extractor class that implements the same interface,
making it easy to switch between languages while maintaining a consistent API.
"""

# Import extractors to make them available at the package level
from .en import EnglishExtractor
from .de import GermanExtractor
from .es import SpanishExtractor
from .fr import FrenchExtractor
from .pl import PolishExtractor

__all__ = [
    'EnglishExtractor',
    'GermanExtractor',
    'SpanishExtractor',
    'FrenchExtractor',
    'PolishExtractor',
]
