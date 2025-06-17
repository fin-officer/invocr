"""
Base classes for invoice extraction.

This module provides the base classes and interfaces for implementing
invoice extractors that can process PDF documents and extract structured
invoice data.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic, Type
from dataclasses import asdict
import re
import logging
from datetime import datetime

from .models import Invoice, InvoiceItem, ContactInfo as Party, Address, PaymentInfo as PaymentTerms

# Type variable for extractor configuration
T = TypeVar('T')

class ExtractionResult:
    """Container for extraction results with confidence scoring."""
    
    def __init__(self, 
                 data: Optional[Any] = None, 
                 confidence: float = 0.0, 
                 extractor: Optional[str] = None,
                 raw_data: Optional[Dict[str, Any]] = None):
        """Initialize extraction result.
        
        Args:
            data: Extracted data (e.g., Invoice, InvoiceItem, etc.)
            confidence: Confidence score (0.0 to 1.0)
            extractor: Name of the extractor that produced this result
            raw_data: Raw extracted data for debugging/validation
        """
        self.data = data
        self.confidence = max(0.0, min(1.0, confidence))
        self.extractor = extractor or "unknown"
        self.raw_data = raw_data or {}
    
    def is_valid(self, min_confidence: float = 0.5) -> bool:
        """Check if the result meets minimum confidence threshold."""
        return self.confidence >= min_confidence and self.data is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'data': asdict(self.data) if hasattr(self.data, 'to_dict') else self.data,
            'confidence': self.confidence,
            'extractor': self.extractor,
            'raw_data': self.raw_data
        }


class FieldExtractor(ABC, Generic[T]):
    """Base class for field extractors."""
    
    def __init__(self, field_name: str, **kwargs):
        self.field_name = field_name
        self.kwargs = kwargs
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        """Extract a specific field from text.
        
        Args:
            text: Text to extract from
            context: Additional context from previous extractions
            
        Returns:
            ExtractionResult containing the extracted value and confidence
        """
        pass
    
    def _log_extraction(self, value: Any, confidence: float):
        """Log extraction result."""
        self.logger.debug(
            "Extracted %s: %s (confidence: %.2f)", 
            self.field_name, 
            value, 
            confidence
        )


class InvoiceExtractor(ABC):
    """Base class for invoice extractors."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the extractor with optional configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._field_extractors: Dict[str, FieldExtractor] = {}
        self._initialize_field_extractors()
    
    def _initialize_field_extractors(self):
        """Initialize field extractors. Override in subclasses."""
        pass
    
    def register_field_extractor(self, field_name: str, extractor: FieldExtractor):
        """Register a field extractor."""
        self._field_extractors[field_name] = extractor
    
    def get_field_extractor(self, field_name: str) -> Optional[FieldExtractor]:
        """Get a registered field extractor."""
        return self._field_extractors.get(field_name)
    
    @abstractmethod
    def extract(self, text: str, **kwargs) -> ExtractionResult:
        """Extract invoice data from text.
        
        Args:
            text: Text to extract from
            **kwargs: Additional extraction parameters
            
        Returns:
            ExtractionResult containing the extracted invoice and confidence
        """
        pass
    
    def extract_field(self, 
                     field_name: str, 
                     text: str, 
                     context: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        """Extract a specific field using registered extractors."""
        extractor = self.get_field_extractor(field_name)
        if not extractor:
            return ExtractionResult(confidence=0.0)
        
        try:
            return extractor.extract(text, context or {})
        except Exception as e:
            self.logger.error(
                "Error extracting field %s: %s", 
                field_name, 
                str(e),
                exc_info=True
            )
            return ExtractionResult(confidence=0.0)
    
    def merge_results(self, results: List[ExtractionResult], 
                     strategy: str = 'highest_confidence') -> ExtractionResult:
        """Merge multiple extraction results.
        
        Args:
            results: List of extraction results to merge
            strategy: Merge strategy ('highest_confidence', 'average', 'weighted')
            
        Returns:
            Merged extraction result
        """
        if not results:
            return ExtractionResult()
            
        if strategy == 'highest_confidence':
            # Return the result with highest confidence
            return max(results, key=lambda r: r.confidence)
        
        # For other strategies, we'd need to implement more sophisticated merging
        # For now, just return the first valid result
        for result in results:
            if result.is_valid():
                return result
                
        return results[0]  # Fall back to first result
    
    def validate_invoice(self, invoice: Invoice) -> bool:
        """Validate the extracted invoice data.
        
        Args:
            invoice: Extracted invoice data
            
        Returns:
            bool: True if the invoice is valid, False otherwise
        """
        # Basic validation - can be extended in subclasses
        required_fields = [
            'invoice_number',
            'invoice_date',
            'seller.name',
            'buyer.name',
            'total_amount'
        ]
        
        for field_path in required_fields:
            parts = field_path.split('.')
            value = invoice
            
            try:
                for part in parts:
                    value = getattr(value, part, None)
                    if value is None:
                        self.logger.warning("Missing required field: %s", field_path)
                        return False
            except AttributeError:
                self.logger.warning("Invalid field path: %s", field_path)
                return False
        
        return True
