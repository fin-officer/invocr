"""
Extraction validation system using OCR text comparison.

This module provides validation mechanisms to verify extraction results
by comparing them with OCR text to ensure accuracy.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ExtractionValidator:
    """
    Validator for extraction results using OCR text comparison.
    
    This class implements validation mechanisms to verify that extracted
    data matches the OCR text content of the document.
    """
    
    def __init__(self, ocr_text: str, confidence_threshold: float = 0.7):
        """
        Initialize the extraction validator.
        
        Args:
            ocr_text: OCR text content of the document
            confidence_threshold: Minimum confidence threshold for validation
        """
        self.ocr_text = ocr_text
        self.confidence_threshold = confidence_threshold
        
    def validate_field(self, field_name: str, field_value: Any) -> Tuple[bool, float]:
        """
        Validate an extracted field against OCR text.
        
        Args:
            field_name: Name of the extracted field
            field_value: Value of the extracted field
            
        Returns:
            Tuple of (is_valid, confidence_score)
        """
        if field_value is None or field_value == "":
            return False, 0.0
            
        # Convert field value to string for comparison
        value_str = str(field_value)
        
        # Check if value appears in OCR text
        if value_str in self.ocr_text:
            return True, 1.0
            
        # Try to find similar text using fuzzy matching
        similarity = self._calculate_similarity(value_str, self.ocr_text)
        
        is_valid = similarity >= self.confidence_threshold
        return is_valid, similarity
        
    def validate_invoice_data(self, invoice_data: Dict[str, Any]) -> Dict[str, Tuple[bool, float]]:
        """
        Validate extracted invoice data against OCR text.
        
        Args:
            invoice_data: Extracted invoice data
            
        Returns:
            Dictionary mapping field names to (is_valid, confidence) tuples
        """
        validation_results = {}
        
        # Validate top-level fields
        for field_name, field_value in invoice_data.items():
            if field_name == "items" or field_name == "totals":
                continue  # Skip complex fields for separate validation
                
            validation_results[field_name] = self.validate_field(field_name, field_value)
            
        # Validate totals
        if "totals" in invoice_data:
            for total_name, total_value in invoice_data["totals"].items():
                field_key = f"totals.{total_name}"
                validation_results[field_key] = self.validate_field(field_key, total_value)
                
        # Validate items (sample validation of first few items)
        if "items" in invoice_data and invoice_data["items"]:
            for i, item in enumerate(invoice_data["items"][:3]):  # Validate first 3 items
                for item_field, item_value in item.items():
                    field_key = f"items[{i}].{item_field}"
                    validation_results[field_key] = self.validate_field(field_key, item_value)
                    
        return validation_results
        
    def validate_consistency(self, invoice_data: Dict[str, Any]) -> List[str]:
        """
        Validate internal consistency of extracted invoice data.
        
        Args:
            invoice_data: Extracted invoice data
            
        Returns:
            List of consistency issues found
        """
        issues = []
        
        # Check if items and totals are consistent
        if "items" in invoice_data and invoice_data["items"] and "totals" in invoice_data:
            items = invoice_data["items"]
            totals = invoice_data["totals"]
            
            # Calculate sum of item totals
            item_total_sum = sum(item.get("total", 0) for item in items)
            
            # Compare with subtotal
            if "subtotal" in totals:
                subtotal = totals["subtotal"]
                if abs(item_total_sum - subtotal) > 0.01:  # Allow small rounding differences
                    issues.append(f"Item total sum ({item_total_sum}) doesn't match subtotal ({subtotal})")
                    
            # Check if total = subtotal + tax
            if "subtotal" in totals and "tax_amount" in totals and "total" in totals:
                calculated_total = totals["subtotal"] + totals["tax_amount"]
                if abs(calculated_total - totals["total"]) > 0.01:
                    issues.append(f"Calculated total ({calculated_total}) doesn't match total ({totals['total']})")
                    
        return issues
        
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # For long texts, use a windowed approach
        if len(text2) > 1000:
            # Try to find the best matching window
            best_ratio = 0.0
            window_size = min(len(text2), max(100, len(text1) * 5))
            
            for i in range(0, len(text2) - window_size + 1, 50):  # Step by 50 chars
                window = text2[i:i + window_size]
                ratio = SequenceMatcher(None, text1, window).ratio()
                best_ratio = max(best_ratio, ratio)
                
            return best_ratio
        else:
            # For shorter texts, compare directly
            return SequenceMatcher(None, text1, text2).ratio()


def validate_extraction(invoice_data: Dict[str, Any], ocr_text: str) -> Dict[str, Any]:
    """
    Validate extracted invoice data against OCR text.
    
    Args:
        invoice_data: Extracted invoice data
        ocr_text: OCR text content of the document
        
    Returns:
        Dictionary with validation results
    """
    validator = ExtractionValidator(ocr_text)
    
    field_validations = validator.validate_invoice_data(invoice_data)
    consistency_issues = validator.validate_consistency(invoice_data)
    
    # Calculate overall confidence
    valid_fields = sum(1 for is_valid, _ in field_validations.values() if is_valid)
    total_fields = len(field_validations)
    overall_confidence = valid_fields / total_fields if total_fields > 0 else 0.0
    
    return {
        "field_validations": field_validations,
        "consistency_issues": consistency_issues,
        "overall_confidence": overall_confidence,
        "is_valid": overall_confidence >= 0.7 and not consistency_issues
    }
