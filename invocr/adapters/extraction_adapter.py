"""
Adapter for dextra package.

This module re-exports functionality from the dextra package
to maintain backward compatibility with existing code.
"""

# Re-export extraction functionality from dextra
from dextra.base import (
    Extractor,
    FieldExtractor,
    DocumentExtractor,
    ExtractorFactory,
    ExtractionResult,
    DocumentType
)

from dextra.regex_extractor import (
    RegexFieldExtractor,
    RegexInvoiceExtractor,
    RegexReceiptExtractor,
    RegexExtractorFactory
)

from dextra.ml_extractor import (
    MLFieldExtractor,
    MLInvoiceExtractor,
    MLReceiptExtractor,
    MLExtractorFactory
)

from dextra.extractor_factory import UnifiedExtractorFactory
from dextra.integration import ExtractionWorkflow, process_document, batch_process

# For backward compatibility
from dextra import *
