"""
Rule-based invoice extractor implementation.

This module provides a configurable, rule-based extractor for invoice data
that can be adapted to different invoice formats through configuration.
"""
import re
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Optional, Pattern, Tuple, Union, Callable

from .document import Invoice, InvoiceItem, Party, Address, PaymentTerms
from .extractor_base import InvoiceExtractor, FieldExtractor, ExtractionResult

# Type aliases
FieldRule = Dict[str, Any]
FieldRules = Dict[str, List[FieldRule]]

class RuleBasedExtractor(InvoiceExtractor):
    """Rule-based invoice extractor that uses configurable patterns."""
    
    def __init__(self, rules: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize the rule-based extractor.
        
        Args:
            rules: Dictionary of extraction rules
            **kwargs: Additional configuration
        """
        super().__init__(**kwargs)
        self.rules = rules or {}
        self._compiled_patterns: Dict[str, List[Pattern]] = {}
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Compile regex patterns from rules."""
        for field, field_rules in self.rules.get('fields', {}).items():
            self._compiled_patterns[field] = []
            
            for rule in field_rules:
                pattern = rule.get('pattern')
                if not pattern:
                    continue
                    
                try:
                    flags = 0
                    if rule.get('case_insensitive', True):
                        flags |= re.IGNORECASE
                    if rule.get('multiline', True):
                        flags |= re.MULTILINE
                    
                    compiled = re.compile(pattern, flags)
                    self._compiled_patterns[field].append({
                        'pattern': compiled,
                        'group': rule.get('group', 1),
                        'type': rule.get('type', 'str'),
                        'format': rule.get('format'),
                        'post_process': rule.get('post_process')
                    })
                except re.error as e:
                    self.logger.error(
                        "Invalid regex pattern for field %s: %s", 
                        field, 
                        str(e)
                    )
    
    def extract(self, text: str, **kwargs) -> ExtractionResult:
        """Extract invoice data using configured rules.
        
        Args:
            text: Text to extract from
            **kwargs: Additional extraction parameters
            
        Returns:
            ExtractionResult containing the extracted invoice
        """
        invoice = Invoice()
        raw_data = {}
        
        # Extract fields using configured rules
        for field, patterns in self._compiled_patterns.items():
            if not patterns:
                continue
                
            # Special handling for nested fields (e.g., 'seller.name')
            if '.' in field:
                # Handle nested fields later
                continue
                
            result = self._extract_field(field, text)
            if result.is_valid():
                setattr(invoice, field, result.data)
                raw_data[field] = result.raw_data
        
        # Handle nested fields after all top-level fields are processed
        self._process_nested_fields(invoice, text, raw_data)
        
        # Post-process the invoice to fill in derived fields
        self._post_process_invoice(invoice)
        
        # Calculate confidence based on extracted fields
        confidence = self._calculate_confidence(invoice)
        
        return ExtractionResult(
            data=invoice,
            confidence=confidence,
            extractor=self.__class__.__name__,
            raw_data=raw_data
        )
    
    def _extract_field(self, field: str, text: str) -> ExtractionResult:
        """Extract a single field using its patterns."""
        patterns = self._compiled_patterns.get(field, [])
        
        for pattern_info in patterns:
            pattern = pattern_info['pattern']
            group = pattern_info['group']
            value_type = pattern_info['type']
            
            match = pattern.search(text)
            if not match:
                continue
                
            try:
                # Extract the matched group
                if isinstance(group, int):
                    value = match.group(group)
                else:  # dict for named groups
                    value = match.groupdict().get(group, '')
                
                if not value:
                    continue
                
                # Convert to appropriate type
                value = self._convert_value(value, value_type, pattern_info.get('format'))
                
                # Apply post-processing if specified
                post_process = pattern_info.get('post_process')
                if post_process:
                    value = self._apply_post_process(value, post_process)
                
                return ExtractionResult(
                    data=value,
                    confidence=0.9,  # High confidence for pattern matches
                    extractor=self.__class__.__name__,
                    raw_data={'match': match.group(0), 'groups': match.groups()}
                )
                
            except (IndexError, ValueError, AttributeError) as e:
                self.logger.debug(
                    "Error extracting field %s: %s", 
                    field, 
                    str(e)
                )
                continue
        
        return ExtractionResult(confidence=0.0)
    
    def _process_nested_fields(self, 
                            invoice: Invoice, 
                            text: str, 
                            raw_data: Dict[str, Any]):
        """Process fields with dot notation (e.g., 'seller.name')."""
        nested_fields = {}
        
        # Group fields by their parent
        for field in self._compiled_patterns.keys():
            if '.' in field:
                parent, child = field.split('.', 1)
                if parent not in nested_fields:
                    nested_fields[parent] = {}
                nested_fields[parent][child] = field
        
        # Process each parent object
        for parent, children in nested_fields.items():
            parent_obj = getattr(invoice, parent, None)
            if parent_obj is None:
                # Create the parent object if it doesn't exist
                parent_obj = self._create_nested_object(parent)
                if parent_obj is not None:
                    setattr(invoice, parent, parent_obj)
                else:
                    continue
            
            # Process each child field
            for child, full_field in children.items():
                result = self._extract_field(full_field, text)
                if result.is_valid():
                    try:
                        # Handle nested attributes (e.g., address.street)
                        parts = child.split('.')
                        obj = parent_obj
                        
                        # Navigate to the parent of the leaf attribute
                        for part in parts[:-1]:
                            if not hasattr(obj, part):
                                setattr(obj, part, {})
                            obj = getattr(obj, part)
                        
                        # Set the leaf attribute
                        setattr(obj, parts[-1], result.data)
                        
                        # Store raw data
                        if parent not in raw_data:
                            raw_data[parent] = {}
                        
                        current = raw_data[parent]
                        for part in parts[:-1]:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = result.raw_data
                        
                    except (AttributeError, TypeError) as e:
                        self.logger.debug(
                            "Error setting nested field %s: %s", 
                            full_field, 
                            str(e)
                        )
    
    def _create_nested_object(self, field_name: str) -> Any:
        """Create an appropriate object for a nested field."""
        # Map common field names to their corresponding classes
        class_map = {
            'seller': Party,
            'buyer': Party,
            'address': Address,
            'payment_terms': PaymentTerms,
            'items': list
        }
        
        obj_class = class_map.get(field_name)
        if obj_class is list:
            return []
        elif obj_class:
            return obj_class()
        return {}
    
    def extract_invoice(self, text: str) -> 'Invoice':
        """Extract invoice data from text.
        
        Args:
            text: Text content to extract invoice data from
            
        Returns:
            Invoice: Extracted invoice data
        """
        result = self.extract(text)
        if result.is_valid():
            return result.data
        return Invoice()

    def _post_process_invoice(self, invoice: Invoice):
        """Post-process the extracted invoice to fill in derived fields."""
        # Set issue date to invoice date if not specified
        if invoice.invoice_date and not invoice.issue_date:
            invoice.issue_date = invoice.invoice_date
        
        # Calculate total from items if not set
        if invoice.items and not invoice.total_amount:
            invoice.subtotal = sum(
                item.total_amount or Decimal('0') 
                for item in invoice.items
            )
            
            if invoice.tax_amount is not None and invoice.subtotal is not None:
                invoice.total_amount = invoice.subtotal + invoice.tax_amount
            else:
                invoice.total_amount = invoice.subtotal
        
        # Set amount due if not specified
        if invoice.total_amount is not None and invoice.amount_paid is not None:
            invoice.amount_due = invoice.total_amount - invoice.amount_paid
    
    def _calculate_confidence(self, invoice: Invoice) -> float:
        """Calculate confidence score based on extracted fields."""
        required_fields = [
            ('invoice_number', 0.2),
            ('invoice_date', 0.2),
            ('seller.name', 0.2),
            ('buyer.name', 0.1),
            ('total_amount', 0.3)
        ]
        
        confidence = 0.0
        
        for field_path, weight in required_fields:
            value = invoice
            parts = field_path.split('.')
            
            try:
                for part in parts:
                    value = getattr(value, part, None)
                    if value is None:
                        break
                
                if value is not None:
                    confidence += weight
            except (AttributeError, TypeError):
                pass
        
        return min(1.0, max(0.0, confidence))
    
    @staticmethod
    def _convert_value(value: str, value_type: str, format_str: Optional[str] = None) -> Any:
        """Convert string value to specified type."""
        if not value:
            return None
            
        try:
            if value_type == 'int':
                return int(re.sub(r'[^\d-]', '', value))
            elif value_type == 'float':
                return float(re.sub(r'[^\d.-]', '', value).replace(',', '.'))
            elif value_type == 'decimal':
                from decimal import Decimal
                return Decimal(re.sub(r'[^\d.-]', '', value).replace(',', '.'))
            elif value_type == 'date':
                if format_str:
                    return datetime.strptime(value.strip(), format_str).date()
                else:
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']:
                        try:
                            return datetime.strptime(value.strip(), fmt).date()
                        except ValueError:
                            continue
                    return value  # Return as string if no format matches
            elif value_type == 'bool':
                return value.lower() in ('true', 'yes', '1', 't', 'y')
            else:  # str or unknown
                return value.strip()
        except (ValueError, TypeError) as e:
            logging.debug("Error converting value '%s' to %s: %s", value, value_type, str(e))
            return value  # Return original value if conversion fails
    
    @staticmethod
    def _apply_post_process(value: Any, post_process: Union[str, dict]) -> Any:
        """Apply post-processing to a value."""
        if isinstance(post_process, str):
            # Simple string replacement
            if '|' in post_process:
                old, new = post_process.split('|', 1)
                return str(value).replace(old, new)
        elif isinstance(post_process, dict):
            # More complex processing
            if post_process.get('type') == 'lookup':
                mapping = post_process.get('mapping', {})
                return mapping.get(str(value).lower(), value)
            elif post_process.get('type') == 'regex_replace':
                import re
                pattern = post_process.get('pattern', '')
                replacement = post_process.get('replacement', '')
                return re.sub(pattern, replacement, str(value))
        
        return value
