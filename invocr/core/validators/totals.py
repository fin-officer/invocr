"""
Totals validation module for InvOCR
Validates invoice totals (subtotal, tax, total)
"""

from typing import Any, Dict, List, Tuple

from .base import BaseValidator, ValidationError

class TotalsValidator(BaseValidator):
    """Validator for invoice totals"""
    
    def __init__(self):
        """Initialize the totals validator"""
        super().__init__()
        self.required_totals_fields = ["total"]
        
    def validate_totals(self, totals: Dict[str, float], items: List[Dict[str, Any]]) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Validate invoice totals
        
        Args:
            totals: Totals dictionary
            items: List of item dictionaries for cross-validation
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check if totals is empty
        if not totals:
            errors.append(self._create_error(
                "totals",
                "Invoice totals information is empty",
                totals
            ))
            return errors, warnings
            
        # Check required fields
        for field in self.required_totals_fields:
            if field not in totals or totals[field] is None:
                errors.append(self._create_error(
                    f"totals.{field}",
                    f"Required total field '{field}' is missing",
                    None
                ))
                
        # Validate subtotal if present
        if "subtotal" in totals and totals["subtotal"] is not None:
            subtotal = totals["subtotal"]
            
            # Check if subtotal is numeric
            if not isinstance(subtotal, (int, float)):
                errors.append(self._create_error(
                    "totals.subtotal",
                    "Subtotal must be a number",
                    subtotal,
                    "Provide a numeric subtotal"
                ))
                
            # Check if subtotal is negative
            elif subtotal < 0:
                errors.append(self._create_error(
                    "totals.subtotal",
                    "Subtotal cannot be negative",
                    subtotal,
                    "Provide a positive subtotal"
                ))
                
            # Cross-validate with items if available
            if items:
                item_totals = [item.get("total_price", 0) for item in items 
                              if "total_price" in item and isinstance(item["total_price"], (int, float))]
                if item_totals:
                    items_sum = round(sum(item_totals), 2)
                    subtotal_rounded = round(subtotal, 2)
                    
                    if abs(items_sum - subtotal_rounded) > 0.01:
                        warnings.append(self._create_warning(
                            "totals.subtotal",
                            f"Subtotal ({subtotal_rounded}) doesn't match sum of item totals ({items_sum})",
                            subtotal,
                            f"Expected subtotal: {items_sum}"
                        ))
                        
        # Validate tax amount if present
        if "tax_amount" in totals and totals["tax_amount"] is not None:
            tax_amount = totals["tax_amount"]
            
            # Check if tax amount is numeric
            if not isinstance(tax_amount, (int, float)):
                errors.append(self._create_error(
                    "totals.tax_amount",
                    "Tax amount must be a number",
                    tax_amount,
                    "Provide a numeric tax amount"
                ))
                
            # Check if tax amount is negative
            elif tax_amount < 0:
                errors.append(self._create_error(
                    "totals.tax_amount",
                    "Tax amount cannot be negative",
                    tax_amount,
                    "Provide a positive tax amount"
                ))
                
            # Check if tax amount is suspiciously high
            if "subtotal" in totals and isinstance(totals["subtotal"], (int, float)) and totals["subtotal"] > 0:
                tax_rate = tax_amount / totals["subtotal"]
                if tax_rate > 0.5:  # More than 50% tax rate
                    warnings.append(self._create_warning(
                        "totals.tax_amount",
                        f"Tax amount ({tax_amount}) is unusually high ({tax_rate:.0%} of subtotal)",
                        tax_amount,
                        "Verify tax amount is correct"
                    ))
                    
        # Validate total if present
        if "total" in totals and totals["total"] is not None:
            total = totals["total"]
            
            # Check if total is numeric
            if not isinstance(total, (int, float)):
                errors.append(self._create_error(
                    "totals.total",
                    "Total must be a number",
                    total,
                    "Provide a numeric total"
                ))
                
            # Check if total is negative
            elif total < 0:
                errors.append(self._create_error(
                    "totals.total",
                    "Total cannot be negative",
                    total,
                    "Provide a positive total"
                ))
                
            # Check if total matches subtotal + tax
            if ("subtotal" in totals and totals["subtotal"] is not None and
                "tax_amount" in totals and totals["tax_amount"] is not None and
                isinstance(totals["subtotal"], (int, float)) and
                isinstance(totals["tax_amount"], (int, float))):
                
                expected_total = round(totals["subtotal"] + totals["tax_amount"], 2)
                total_rounded = round(total, 2)
                
                if abs(expected_total - total_rounded) > 0.01:
                    warnings.append(self._create_warning(
                        "totals.total",
                        f"Total ({total_rounded}) doesn't match subtotal + tax ({expected_total})",
                        total,
                        f"Expected total: {expected_total}"
                    ))
                    
        return errors, warnings
