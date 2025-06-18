"""
Regex-based extractor with validation capabilities.

This module provides a specialized extractor that uses regex patterns for data extraction
and includes validation to ensure the extracted data is correct.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Pattern
from dataclasses import dataclass, field

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor
from invocr.formats.pdf.extractors.specialized.validation import DataValidator, ValidationRules

logger = get_logger(__name__)


@dataclass
class ExtractionPattern:
    """Data class for regex extraction patterns with validation."""
    name: str
    pattern: str
    validation_type: str
    compiled_pattern: Pattern = None
    description: str = ""
    group_index: int = 1
    flags: int = re.IGNORECASE
    fallback_patterns: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Compile the regex pattern after initialization."""
        self.compiled_pattern = re.compile(self.pattern, self.flags)
        self.fallback_compiled = [
            re.compile(pattern, self.flags) for pattern in self.fallback_patterns
        ]


class RegexExtractor(BaseInvoiceExtractor):
    """
    Specialized extractor using regex patterns with validation.
    
    This extractor uses configurable regex patterns to extract data from documents
    and validates the extracted data using the validation rules.
    """
    
    def __init__(self, patterns: Optional[Dict[str, Dict]] = None, 
                 validation_rules: Optional[Dict[str, str]] = None):
        """
        Initialize the regex extractor.
        
        Args:
            patterns: Dictionary of field patterns
            validation_rules: Dictionary mapping fields to validation types
        """
        super().__init__()
        self.logger = logger
        self.validator = DataValidator()
        
        # Default patterns for common fields
        self._default_patterns = {
            "invoice_number": ExtractionPattern(
                name="invoice_number",
                pattern=r"(?:invoice|faktura|rechnung)(?:\s+(?:no|nr|number|nummer):?)?(?:\s+|:\s*)([A-Za-z0-9\-\/]+)",
                validation_type="text",
                description="Invoice number"
            ),
            "issue_date": ExtractionPattern(
                name="issue_date",
                pattern=r"(?:date|data|datum|fecha)(?:\s+(?:of|issued|wystawienia):?)?(?:\s+|:\s*)(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})",
                validation_type="date",
                description="Invoice issue date",
                fallback_patterns=[
                    r"(?:issue|invoice|data|datum)\s+date:?\s*(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})",
                    r"(?:date|data):?\s*(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})"
                ]
            ),
            "due_date": ExtractionPattern(
                name="due_date",
                pattern=r"(?:due|payment|płatność)\s+(?:date|termin):?\s*(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})",
                validation_type="date",
                description="Payment due date"
            ),
            "total_amount": ExtractionPattern(
                name="total_amount",
                pattern=r"(?:total|suma|gesamtbetrag|total|total)(?:\s+(?:amount|kwota|betrag|montant|importe):?)?(?:\s+|:\s*)([€£$]?\s*[\d\s,.]+)",
                validation_type="currency",
                description="Total invoice amount",
                fallback_patterns=[
                    r"(?:total|suma|gesamtbetrag):?\s*([€£$]?\s*[\d\s,.]+)",
                    r"(?:amount\s+due):?\s*([€£$]?\s*[\d\s,.]+)"
                ]
            ),
            "tax_amount": ExtractionPattern(
                name="tax_amount",
                pattern=r"(?:tax|vat|mwst|ust|iva|tva|podatek)(?:\s+(?:amount|kwota|betrag|montant|importe):?)?(?:\s+|:\s*)([€£$]?\s*[\d\s,.]+)",
                validation_type="currency",
                description="Tax amount"
            ),
            "tax_rate": ExtractionPattern(
                name="tax_rate",
                pattern=r"(?:tax|vat|mwst|ust|iva|tva|podatek)(?:\s+(?:rate|stawka|satz|taux|tasa):?)?(?:\s+|:\s*)(\d{1,2}(?:\.\d{1,2})?%?)",
                validation_type="percentage",
                description="Tax rate"
            ),
            "vendor_name": ExtractionPattern(
                name="vendor_name",
                pattern=r"(?:vendor|seller|sprzedawca|verkäufer|vendeur|vendedor):?\s*([A-Za-z0-9\s\.,]+)(?:\n|$)",
                validation_type="text",
                description="Vendor name"
            ),
            "vendor_tax_id": ExtractionPattern(
                name="vendor_tax_id",
                pattern=r"(?:tax\s+id|vat\s+id|nip|ust-id|siret|cif):?\s*([A-Za-z0-9\s\-\.\/]+)(?:\n|$)",
                validation_type="tax_id",
                description="Vendor tax ID"
            ),
            "customer_name": ExtractionPattern(
                name="customer_name",
                pattern=r"(?:customer|buyer|nabywca|käufer|acheteur|comprador|bill\s+to):?\s*([A-Za-z0-9\s\.,]+)(?:\n|$)",
                validation_type="text",
                description="Customer name"
            ),
            "currency": ExtractionPattern(
                name="currency",
                pattern=r"(?:currency|waluta|währung|devise|moneda):?\s*([A-Z]{3})",
                validation_type="text",
                description="Currency code"
            )
        }
        
        # Initialize patterns
        self.patterns = {}
        self._initialize_patterns(patterns or {})
        
        # Initialize validation rules
        self.validation_rules = validation_rules or {
            "issue_date": "date",
            "due_date": "date",
            "total_amount": "currency",
            "tax_amount": "currency",
            "tax_rate": "percentage",
            "vendor_tax_id": "tax_id"
        }
    
    def _initialize_patterns(self, custom_patterns: Dict[str, Dict]) -> None:
        """
        Initialize extraction patterns with custom overrides.
        
        Args:
            custom_patterns: Dictionary of custom patterns
        """
        # Start with default patterns
        self.patterns = self._default_patterns.copy()
        
        # Override with custom patterns
        for field_name, pattern_info in custom_patterns.items():
            if isinstance(pattern_info, dict):
                self.patterns[field_name] = ExtractionPattern(
                    name=field_name,
                    pattern=pattern_info.get("pattern", ""),
                    validation_type=pattern_info.get("validation_type", "text"),
                    description=pattern_info.get("description", ""),
                    group_index=pattern_info.get("group_index", 1),
                    flags=pattern_info.get("flags", re.IGNORECASE),
                    fallback_patterns=pattern_info.get("fallback_patterns", [])
                )
            else:
                # Simple string pattern
                self.patterns[field_name] = ExtractionPattern(
                    name=field_name,
                    pattern=pattern_info,
                    validation_type="text"
                )
    
    def extract_field(self, text: str, field_name: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Extract a field from text using the configured pattern.
        
        Args:
            text: Text to extract from
            field_name: Name of the field to extract
            
        Returns:
            Tuple of (extracted_value, extraction_info)
        """
        if field_name not in self.patterns:
            self.logger.warning(f"No pattern defined for field '{field_name}'")
            return None, {"success": False, "error": f"No pattern defined for field '{field_name}'"}
        
        pattern = self.patterns[field_name]
        extraction_info = {
            "field": field_name,
            "pattern": pattern.pattern,
            "success": False,
            "validation_type": pattern.validation_type
        }
        
        # Try primary pattern
        match = pattern.compiled_pattern.search(text)
        if match:
            value = match.group(pattern.group_index).strip()
            extraction_info["success"] = True
            extraction_info["match_position"] = match.start()
            extraction_info["match_text"] = match.group(0)
            
            # Validate the extracted value
            if pattern.validation_type:
                validation_result = self.validator.validate_field(
                    field_name, value, pattern.validation_type
                )
                extraction_info["valid"] = validation_result["valid"]
                if not validation_result["valid"]:
                    extraction_info["validation_error"] = validation_result.get("error", "Validation failed")
            
            return value, extraction_info
        
        # Try fallback patterns
        for i, fallback_pattern in enumerate(pattern.fallback_compiled):
            match = fallback_pattern.search(text)
            if match:
                value = match.group(pattern.group_index).strip()
                extraction_info["success"] = True
                extraction_info["match_position"] = match.start()
                extraction_info["match_text"] = match.group(0)
                extraction_info["fallback_index"] = i
                
                # Validate the extracted value
                if pattern.validation_type:
                    validation_result = self.validator.validate_field(
                        field_name, value, pattern.validation_type
                    )
                    extraction_info["valid"] = validation_result["valid"]
                    if not validation_result["valid"]:
                        extraction_info["validation_error"] = validation_result.get("error", "Validation failed")
                
                return value, extraction_info
        
        # No match found
        return None, extraction_info
    
    def extract_data(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract data from document text using regex patterns.
        
        Args:
            text: Document text content
            metadata: Optional document metadata
            
        Returns:
            Dictionary of extracted fields
        """
        metadata = metadata or {}
        results = {
            "metadata": metadata,
            "extraction_info": {}
        }
        
        # Extract each field
        for field_name in self.patterns.keys():
            self.logger.info(f"Extracting field: {field_name}")
            value, extraction_info = self.extract_field(text, field_name)
            
            if value:
                results[field_name] = value
            
            results["extraction_info"][field_name] = extraction_info
            
            # Log extraction result
            if extraction_info["success"]:
                self.logger.info(f"Successfully extracted {field_name}: {value}")
                if "valid" in extraction_info and not extraction_info["valid"]:
                    self.logger.warning(f"Validation failed for {field_name}: {extraction_info.get('validation_error', 'Unknown error')}")
            else:
                self.logger.info(f"Failed to extract {field_name}")
        
        # Extract line items (if applicable)
        if "line_items" in self.patterns:
            line_items = self._extract_line_items(text)
            if line_items:
                results["line_items"] = line_items
        
        # Validate totals consistency
        if "line_items" in results and "total_amount" in results:
            totals_validation = self.validator.validate_totals_consistency(results)
            results["extraction_info"]["totals_validation"] = totals_validation
            
            if not totals_validation["valid"]:
                self.logger.warning(f"Totals validation failed: {totals_validation['errors']}")
        
        return results
    
    def _extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract line items from the document text.
        
        Args:
            text: Document text content
            
        Returns:
            List of line item dictionaries
        """
        line_items = []
        
        # This is a simplified implementation
        # A real implementation would need to handle different table formats
        # and extract structured line item data
        
        # Example pattern for line items
        line_item_pattern = re.compile(
            r"(\d+)\s+([A-Za-z0-9\s\.,]+)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)",
            re.MULTILINE
        )
        
        for match in line_item_pattern.finditer(text):
            item = {
                "quantity": match.group(1),
                "description": match.group(2).strip(),
                "unit_price": match.group(3),
                "tax_rate": match.group(4),
                "amount": match.group(5)
            }
            line_items.append(item)
        
        return line_items
    
    def register_pattern(self, field_name: str, pattern: str, validation_type: str = "text", 
                        description: str = "", group_index: int = 1, 
                        fallback_patterns: List[str] = None) -> None:
        """
        Register a new extraction pattern.
        
        Args:
            field_name: Name of the field
            pattern: Regex pattern string
            validation_type: Type of validation to apply
            description: Description of the field
            group_index: Capture group index for the value
            fallback_patterns: List of fallback patterns
        """
        self.patterns[field_name] = ExtractionPattern(
            name=field_name,
            pattern=pattern,
            validation_type=validation_type,
            description=description,
            group_index=group_index,
            fallback_patterns=fallback_patterns or []
        )
        self.logger.info(f"Registered pattern for field '{field_name}'")
    
    def load_patterns_from_file(self, file_path: str) -> None:
        """
        Load extraction patterns from a JSON file.
        
        Args:
            file_path: Path to the JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                pattern_data = json.load(f)
            
            self._initialize_patterns(pattern_data)
            self.logger.info(f"Loaded {len(pattern_data)} patterns from {file_path}")
        except Exception as e:
            self.logger.error(f"Error loading patterns from {file_path}: {e}")
            raise
