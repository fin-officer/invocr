"""
PDF processing package for InvOCR
Contains modules for PDF processing and data extraction
"""

from .converter import extract_tables, get_page_count, pdf_to_images, pdf_to_text
# Import extraction functions from their new locations
from .extractors.date_utils import extract_date
from .extractors.item_utils import extract_items
from .extractors.totals_utils import extract_totals
from .extractors.base_extractor import BaseInvoiceExtractor
from .extractors.extractor_factory import PDFExtractorFactory

# Import compatibility functions that actually exist in the new extractor
from .extractor import (
    extract_items,
    extract_total_amount,
    extract_tax_amount,
    extract_currency,
    extract_issue_date,
    extract_due_date,
)
from .models import (
    Address,
    ContactInfo,
    Invoice,
    InvoiceItem,
    InvoiceTotals,
    PaymentInfo,
)
from .processor import PDFProcessor


def extract_invoice_data(input_file, rules=None, languages=None):
    """
    Extract invoice data from a PDF file.
    This is a compatibility function that wraps the refactored extractor functionality.
    
    Args:
        input_file: Path to PDF file
        rules: Optional rules to use for extraction
        languages: Optional list of languages for OCR
        
    Returns:
        Dictionary with extracted invoice data
    """
    from pathlib import Path
    
    # Process PDF and extract text
    processor = PDFProcessor(input_file)
    text = processor.get_text()
    
    # Create extractor based on document type
    factory = PDFExtractorFactory()
    document_type = factory.detect_document_type(text)
    extractor = factory.create_extractor(document_type=document_type, rules=rules)
    
    # Extract data
    invoice = extractor.extract(text)
    
    # Convert to dictionary if it's not already
    if hasattr(invoice, 'to_dict'):
        return invoice.to_dict()
    return invoice

__all__ = [
    "Invoice",
    "InvoiceItem",
    "InvoiceTotals",
    "Address",
    "ContactInfo",
    "PaymentInfo",
    "PDFProcessor",
    "BaseInvoiceExtractor",
    "PDFExtractorFactory",
    "extract_invoice_data",
    "extract_document_number",
    "extract_date",
    "extract_party",
    "extract_items",
    "extract_totals",
    "extract_payment_terms",
    "extract_notes",
    "pdf_to_text",
    "pdf_to_images",
    "pdf_to_json",
    "get_page_count",
    "extract_tables",
]
