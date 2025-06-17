"""
Cross-field validation module for InvOCR
Validates relationships between different invoice fields
"""

from typing import Any, Dict, List, Tuple

from .base import BaseValidator, ValidationError

class CrossFieldValidator(BaseValidator):
    """Validator for cross-field relationships"""
    
    def __init__(self):
        """Initialize the cross-field validator"""
        super().__init__()
        
    def validate_cross_fields(self, data: Dict[str, Any]) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Validate relationships between different invoice fields
        
        Args:
            data: Invoice data dictionary
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check if seller and buyer are the same
        if "seller" in data and "buyer" in data:
            seller = data["seller"]
            buyer = data["buyer"]
            
            if (seller.get("name") and buyer.get("name") and 
                seller.get("name").strip().lower() == buyer.get("name").strip().lower()):
                warnings.append(self._create_warning(
                    "buyer.name",
                    "Seller and buyer names are identical",
                    buyer.get("name"),
                    "Verify seller and buyer are different entities"
                ))
                
            if (seller.get("tax_id") and buyer.get("tax_id") and 
                seller.get("tax_id").strip() == buyer.get("tax_id").strip()):
                warnings.append(self._create_warning(
                    "buyer.tax_id",
                    "Seller and buyer tax IDs are identical",
                    buyer.get("tax_id"),
                    "Verify seller and buyer are different entities"
                ))
                
        # Check if document has both items and totals
        if "items" in data and "totals" in data:
            items = data["items"]
            totals = data["totals"]
            
            # If there are items but no total
            if items and "total" not in totals:
                errors.append(self._create_error(
                    "totals.total",
                    "Invoice has items but no total amount",
                    None,
                    "Add total amount"
                ))
                
            # If there's a total but no items
            if not items and "total" in totals and totals["total"] > 0:
                warnings.append(self._create_warning(
                    "items",
                    "Invoice has a total amount but no line items",
                    totals.get("total"),
                    "Add line items to match the total"
                ))
                
        # Check payment information consistency
        if "payment_method" in data and "bank_account" in data:
            payment_method = data.get("payment_method", "").lower()
            bank_account = data.get("bank_account")
            
            # If payment method is cash but bank account is provided
            if payment_method in ["cash", "card", "credit card"] and bank_account:
                warnings.append(self._create_warning(
                    "bank_account",
                    f"Bank account provided but payment method is {payment_method}",
                    bank_account,
                    "Remove bank account or correct payment method"
                ))
                
            # If payment method is bank transfer but no account is provided
            if payment_method in ["bank transfer", "wire", "transfer"] and not bank_account:
                warnings.append(self._create_warning(
                    "bank_account",
                    f"Payment method is {payment_method} but no bank account provided",
                    None,
                    "Add bank account information"
                ))
                
        # Check for inconsistent currency
        if "currency" in data and "totals" in data and "items" in data:
            currency = data.get("currency")
            items = data.get("items", [])
            
            for i, item in enumerate(items):
                if "currency" in item and item["currency"] != currency:
                    warnings.append(self._create_warning(
                        f"items[{i}].currency",
                        f"Item {i+1} currency ({item['currency']}) doesn't match invoice currency ({currency})",
                        item.get("currency"),
                        f"Use consistent currency ({currency})"
                    ))
                    
        return errors, warnings
