"""
PDF invoice extraction.

This module integrates the new modular extraction system and provides backward compatibility
with the existing code that depends on the original extractor.py interface.
"""

from typing import Dict, List, Any, Optional

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.extractor_factory import PDFExtractorFactory

logger = get_logger(__name__)


class PDFInvoiceExtractor:
    """
    PDF invoice extractor that integrates the new modular extraction system.
    
    This class maintains backward compatibility with existing code while leveraging
    the new modular extraction utilities.
    """
    
    def __init__(self, rules: Optional[Dict] = None, **kwargs):
        """
        Initialize the PDF invoice extractor.
        
        Args:
            rules: Optional dictionary of regex rules for extraction
            **kwargs: Additional parameters for backward compatibility
        """
        self.rules = rules
        self.kwargs = kwargs
        self.factory = PDFExtractorFactory()
    
    def extract(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract invoice data from PDF text.
        
        Args:
            text: The text content to extract from
            metadata: Optional document metadata
            
        Returns:
            Dictionary containing extracted invoice data
        """
        metadata = metadata or {}
        
        # Detect document type
        document_type = self.factory.detect_document_type(text, metadata)
        
        # Create the appropriate extractor
        extractor = self.factory.create_extractor(
            document_type=document_type,
            rules=self.rules,
            format_hints=metadata
        )
        
        # Extract data
        invoice_data = extractor.extract(text)
        
        return invoice_data


# Alias for backward compatibility
extract = PDFInvoiceExtractor().extract

# Main extraction function for backward compatibility
def extract_invoice_data(text: str, rules: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Extract invoice data from text (backward compatibility function).
    
    Args:
        text: Text to extract data from
        rules: Optional dictionary of regex rules for extraction
        
    Returns:
        Dictionary with extracted invoice data
    """
    extractor = PDFInvoiceExtractor(rules=rules)
    return extractor.extract(text)


def extract_items(text: str) -> List[Dict[str, Any]]:
    """
    Extract line items from invoice text (backward compatibility function).
    
    Args:
        text: Text to search for line items
        
    Returns:
        List of dictionaries with item details
    """
    from invocr.formats.pdf.extractors.item_utils import extract_items as extract_items_impl
    return extract_items_impl(text)


def extract_total_amount(text: str) -> float:
    """
    Extract total amount from invoice text (backward compatibility function).
    
    Args:
        text: Text to search for total amount
        
    Returns:
        Extracted total amount as float
    """
    from invocr.formats.pdf.extractors.totals_utils import extract_totals
    totals = extract_totals(text)
    return totals["total_amount"]


def extract_tax_amount(text: str) -> float:
    """
    Extract tax amount from invoice text (backward compatibility function).
    
    Args:
        text: Text to search for tax amount
        
    Returns:
        Extracted tax amount as float
    """
    from invocr.formats.pdf.extractors.totals_utils import extract_totals
    totals = extract_totals(text)
    return totals["tax_amount"]


def extract_currency(text: str) -> str:
    """
    Extract currency from invoice text (backward compatibility function).
    
    Args:
        text: Text to search for currency
        
    Returns:
        Extracted currency code
    """
    from invocr.formats.pdf.extractors.numeric_utils import extract_currency as extract_currency_impl
    return extract_currency_impl(text)


def extract_issue_date(text: str) -> Optional[Any]:
    """
    Extract issue date from invoice text (backward compatibility function).
    
    Args:
        text: Text to search for issue date
        
    Returns:
        Extracted date as datetime.date or None
    """
    from invocr.formats.pdf.extractors.date_utils import extract_date
    date_obj = extract_date(text, date_type="issue")
    if date_obj:
        return date_obj.date()
    return None


def extract_due_date(text: str, issue_date: Optional[Any] = None) -> Optional[Any]:
    """
    Extract due date from invoice text (backward compatibility function).
    
    Args:
        text: Text to search for due date
        issue_date: Optional issue date for relative date calculation
        
    Returns:
        Extracted date as datetime.date or None
    """
    from invocr.formats.pdf.extractors.date_utils import extract_date
    date_obj = extract_date(text, date_type="due", reference_date=issue_date)
    if date_obj:
        return date_obj.date()
    return None
