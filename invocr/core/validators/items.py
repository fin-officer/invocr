"""
Items validation module for InvOCR
Validates invoice line items
"""

from typing import Any, Dict, List, Tuple

from .base import BaseValidator, ValidationError

class ItemsValidator(BaseValidator):
    """Validator for invoice line items"""
    
    def __init__(self):
        """Initialize the items validator"""
        super().__init__()
        self.required_item_fields = [
            "description",
            "quantity",
            "unit_price",
            "total_price",
        ]
        
    def validate_items(self, items: List[Dict[str, Any]]) -> Tuple[List[ValidationError], List[ValidationError], List[str]]:
        """
        Validate invoice line items
        
        Args:
            items: List of item dictionaries
            
        Returns:
            Tuple of (errors, warnings, suggestions)
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Check if items list is empty
        if not items:
            warnings.append(self._create_warning(
                "items",
                "Invoice has no line items",
                items,
                "Add at least one line item"
            ))
            return errors, warnings, suggestions
            
        # Check each item
        for i, item in enumerate(items):
            item_errors, item_warnings = self._validate_item(item, i)
            errors.extend(item_errors)
            warnings.extend(item_warnings)
            
        # Check for duplicate items
        if len(items) > 1:
            descriptions = [item.get("description", "").strip().lower() for item in items if "description" in item]
            duplicate_descriptions = set([desc for desc in descriptions if descriptions.count(desc) > 1])
            
            if duplicate_descriptions:
                for desc in duplicate_descriptions:
                    warnings.append(self._create_warning(
                        "items",
                        f"Possible duplicate item: '{desc}'",
                        desc,
                        "Verify if these are actually different items"
                    ))
                    
        return errors, warnings, suggestions
        
    def _validate_item(self, item: Dict[str, Any], index: int) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Validate a single line item
        
        Args:
            item: Item dictionary
            index: Item index in the list
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.required_item_fields:
            if field not in item or item[field] is None:
                errors.append(self._create_error(
                    f"items[{index}].{field}",
                    f"Item {index+1} is missing required field '{field}'",
                    None
                ))
                
        # Validate description
        if "description" in item and item["description"]:
            description = item["description"]
            
            # Check if description is too short
            if len(description) < 2:
                warnings.append(self._create_warning(
                    f"items[{index}].description",
                    f"Item {index+1} description is unusually short",
                    description,
                    "Provide a more descriptive item name"
                ))
                
            # Check if description is too long
            if len(description) > 200:
                warnings.append(self._create_warning(
                    f"items[{index}].description",
                    f"Item {index+1} description is unusually long",
                    description,
                    "Consider shortening the description"
                ))
                
        # Validate quantity
        if "quantity" in item and item["quantity"] is not None:
            quantity = item["quantity"]
            
            # Check if quantity is numeric
            if not isinstance(quantity, (int, float)):
                errors.append(self._create_error(
                    f"items[{index}].quantity",
                    f"Item {index+1} quantity must be a number",
                    quantity,
                    "Provide a numeric quantity"
                ))
                
            # Check if quantity is negative
            elif quantity < 0:
                errors.append(self._create_error(
                    f"items[{index}].quantity",
                    f"Item {index+1} quantity cannot be negative",
                    quantity,
                    "Provide a positive quantity"
                ))
                
            # Check if quantity is zero
            elif quantity == 0:
                warnings.append(self._create_warning(
                    f"items[{index}].quantity",
                    f"Item {index+1} has zero quantity",
                    quantity,
                    "Verify if this item should be included"
                ))
                
        # Validate unit price
        if "unit_price" in item and item["unit_price"] is not None:
            unit_price = item["unit_price"]
            
            # Check if unit price is numeric
            if not isinstance(unit_price, (int, float)):
                errors.append(self._create_error(
                    f"items[{index}].unit_price",
                    f"Item {index+1} unit price must be a number",
                    unit_price,
                    "Provide a numeric unit price"
                ))
                
            # Check if unit price is negative
            elif unit_price < 0:
                errors.append(self._create_error(
                    f"items[{index}].unit_price",
                    f"Item {index+1} unit price cannot be negative",
                    unit_price,
                    "Provide a positive unit price"
                ))
                
        # Validate total price
        if "total_price" in item and item["total_price"] is not None:
            total_price = item["total_price"]
            
            # Check if total price is numeric
            if not isinstance(total_price, (int, float)):
                errors.append(self._create_error(
                    f"items[{index}].total_price",
                    f"Item {index+1} total price must be a number",
                    total_price,
                    "Provide a numeric total price"
                ))
                
            # Check if total price is negative
            elif total_price < 0:
                errors.append(self._create_error(
                    f"items[{index}].total_price",
                    f"Item {index+1} total price cannot be negative",
                    total_price,
                    "Provide a positive total price"
                ))
                
            # Check if total price matches quantity * unit price
            if ("quantity" in item and item["quantity"] is not None and 
                "unit_price" in item and item["unit_price"] is not None and
                isinstance(item["quantity"], (int, float)) and
                isinstance(item["unit_price"], (int, float))):
                
                expected_total = round(item["quantity"] * item["unit_price"], 2)
                actual_total = round(total_price, 2)
                
                if abs(expected_total - actual_total) > 0.01:
                    warnings.append(self._create_warning(
                        f"items[{index}].total_price",
                        f"Item {index+1} total price ({actual_total}) doesn't match quantity * unit price ({expected_total})",
                        total_price,
                        f"Expected total: {expected_total}"
                    ))
                    
        return errors, warnings
