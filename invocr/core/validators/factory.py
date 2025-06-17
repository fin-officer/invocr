"""
Factory module for invoice validators
Provides factory functions to create and use validators
"""

from typing import Any, Dict

from .base import ValidationResult
from .document import DocumentValidator
from .party import PartyValidator
from .items import ItemsValidator
from .totals import TotalsValidator
from .cross_field import CrossFieldValidator

from ...utils.logger import get_logger

logger = get_logger(__name__)


class InvoiceValidator:
    """Main invoice validator that orchestrates all validation components"""
    
    def __init__(self):
        """Initialize the invoice validator with all component validators"""
        self.document_validator = DocumentValidator()
        self.party_validator = PartyValidator()
        self.items_validator = ItemsValidator()
        self.totals_validator = TotalsValidator()
        self.cross_field_validator = CrossFieldValidator()
        
        self.required_fields = [
            "document_number",
            "document_date",
            "seller",
            "buyer",
            "items",
            "totals",
        ]
        
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Comprehensive validation of invoice data
        
        Args:
            data: Invoice data dictionary
            
        Returns:
            ValidationResult with errors, warnings and quality score
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Basic structure validation
        structure_errors = self._validate_structure(data)
        errors.extend(structure_errors)
        
        # Field-specific validations
        if "document_number" in data:
            doc_errors, doc_warnings = self.document_validator.validate_document_number(
                data["document_number"]
            )
            errors.extend(doc_errors)
            warnings.extend(doc_warnings)
            
        if "document_date" in data:
            date_errors, date_warnings = self.document_validator.validate_dates(data)
            errors.extend(date_errors)
            warnings.extend(date_warnings)
            
        if "seller" in data:
            seller_errors, seller_warnings = self.party_validator.validate_party(
                data["seller"], "seller"
            )
            errors.extend(seller_errors)
            warnings.extend(seller_warnings)
            
        if "buyer" in data:
            buyer_errors, buyer_warnings = self.party_validator.validate_party(
                data["buyer"], "buyer"
            )
            errors.extend(buyer_errors)
            warnings.extend(buyer_warnings)
            
        if "items" in data:
            items_errors, items_warnings, items_suggestions = self.items_validator.validate_items(
                data["items"]
            )
            errors.extend(items_errors)
            warnings.extend(items_warnings)
            suggestions.extend(items_suggestions)
            
        if "totals" in data:
            totals_errors, totals_warnings = self.totals_validator.validate_totals(
                data["totals"], data.get("items", [])
            )
            errors.extend(totals_errors)
            warnings.extend(totals_warnings)
            
        # Cross-field validations
        cross_errors, cross_warnings = self.cross_field_validator.validate_cross_fields(data)
        errors.extend(cross_errors)
        warnings.extend(cross_warnings)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(data, errors, warnings)
        
        # Generate suggestions
        suggestions.extend(self._generate_suggestions(data, errors, warnings))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            quality_score=quality_score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )
        
    def _validate_structure(self, data: Dict[str, Any]) -> list:
        """
        Validate the basic structure of invoice data
        
        Args:
            data: Invoice data dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check if data is empty
        if not data:
            errors.append(self.document_validator._create_error(
                "data",
                "Invoice data is empty",
                data
            ))
            return errors
            
        # Check required fields
        for field in self.required_fields:
            if field not in data:
                errors.append(self.document_validator._create_error(
                    field,
                    f"Required field '{field}' is missing",
                    None
                ))
                
        return errors
        
    def _calculate_quality_score(self, data: Dict[str, Any], errors: list, warnings: list) -> float:
        """
        Calculate quality score based on errors and warnings
        
        Args:
            data: Invoice data dictionary
            errors: List of validation errors
            warnings: List of validation warnings
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        # Base score
        score = 1.0
        
        # Deduct for errors
        if errors:
            score -= min(0.5, len(errors) * 0.1)
            
        # Deduct for warnings
        if warnings:
            score -= min(0.3, len(warnings) * 0.05)
            
        # Check completeness of data
        completeness = self._calculate_completeness(data)
        score = score * completeness
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
        
    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """
        Calculate completeness score of invoice data
        
        Args:
            data: Invoice data dictionary
            
        Returns:
            Completeness score between 0.0 and 1.0
        """
        # Define all possible fields for a complete invoice
        all_fields = self.required_fields + [
            "issue_date",
            "due_date",
            "payment_method",
            "currency",
            "notes",
        ]
        
        # Count present fields
        present_fields = sum(1 for field in all_fields if field in data)
        
        # Calculate completeness ratio
        return present_fields / len(all_fields)
        
    def _generate_suggestions(self, data: Dict[str, Any], errors: list, warnings: list) -> list:
        """
        Generate suggestions for improving invoice data
        
        Args:
            data: Invoice data dictionary
            errors: List of validation errors
            warnings: List of validation warnings
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Add suggestions based on errors and warnings
        for error in errors:
            if error.suggestion:
                suggestions.append(error.suggestion)
                
        for warning in warnings:
            if warning.suggestion:
                suggestions.append(warning.suggestion)
                
        # Additional suggestions
        if "currency" not in data:
            suggestions.append("Add currency information")
            
        if "payment_method" not in data:
            suggestions.append("Add payment method information")
            
        if "due_date" not in data and "issue_date" in data:
            suggestions.append("Add due date information")
            
        return suggestions


def create_validator() -> InvoiceValidator:
    """
    Factory function to create a validator instance
    
    Returns:
        InvoiceValidator instance
    """
    return InvoiceValidator()


def validate_invoice_data(data: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate invoice data
    
    Args:
        data: Invoice data dictionary
        
    Returns:
        ValidationResult with errors, warnings and quality score
    """
    validator = create_validator()
    return validator.validate(data)


def is_valid_invoice(data: Dict[str, Any]) -> bool:
    """
    Quick check if invoice data is valid
    
    Args:
        data: Invoice data dictionary
        
    Returns:
        True if valid, False otherwise
    """
    result = validate_invoice_data(data)
    return result.is_valid
