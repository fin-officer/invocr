"""
Party validation module for InvOCR
Validates seller and buyer information
"""

import re
from typing import Any, Dict, List, Tuple

from .base import BaseValidator, ValidationError

class PartyValidator(BaseValidator):
    """Validator for seller and buyer information"""
    
    def __init__(self):
        """Initialize the party validator"""
        super().__init__()
        self.required_seller_fields = ["name"]
        self.required_buyer_fields = ["name"]
        
    def validate_party(self, party_data: Dict[str, Any], party_type: str) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Validate party (seller or buyer) information
        
        Args:
            party_data: Party data dictionary
            party_type: Type of party ('seller' or 'buyer')
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check if party data is empty
        if not party_data:
            errors.append(self._create_error(
                f"{party_type}",
                f"{party_type.capitalize()} information is empty",
                party_data
            ))
            return errors, warnings
            
        # Check required fields
        required_fields = self.required_seller_fields if party_type == "seller" else self.required_buyer_fields
        for field in required_fields:
            if field not in party_data or not party_data[field]:
                errors.append(self._create_error(
                    f"{party_type}.{field}",
                    f"{party_type.capitalize()} {field} is required but missing",
                    None
                ))
                
        # Validate name
        if "name" in party_data and party_data["name"]:
            name = party_data["name"]
            
            # Check if name is too short
            if len(name) < 2:
                warnings.append(self._create_warning(
                    f"{party_type}.name",
                    f"{party_type.capitalize()} name is unusually short",
                    name,
                    f"Verify {party_type} name is complete"
                ))
                
            # Check if name is too long
            if len(name) > 200:
                warnings.append(self._create_warning(
                    f"{party_type}.name",
                    f"{party_type.capitalize()} name is unusually long",
                    name,
                    f"Verify {party_type} name is correct"
                ))
                
        # Validate tax ID if present
        if "tax_id" in party_data and party_data["tax_id"]:
            tax_id = party_data["tax_id"]
            
            # Check tax ID format (basic check)
            if not re.match(r'^[A-Za-z0-9\-]+$', tax_id):
                warnings.append(self._create_warning(
                    f"{party_type}.tax_id",
                    f"{party_type.capitalize()} tax ID contains unusual characters",
                    tax_id,
                    f"Verify {party_type} tax ID is correct"
                ))
                
        # Validate email if present
        if "email" in party_data and party_data["email"]:
            email = party_data["email"]
            
            # Check email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                errors.append(self._create_error(
                    f"{party_type}.email",
                    f"{party_type.capitalize()} email address is invalid",
                    email,
                    "Provide a valid email address"
                ))
                
        # Validate phone if present
        if "phone" in party_data and party_data["phone"]:
            phone = party_data["phone"]
            
            # Check phone format (basic check)
            if not re.match(r'^[0-9+\-() ]+$', phone):
                warnings.append(self._create_warning(
                    f"{party_type}.phone",
                    f"{party_type.capitalize()} phone number contains unusual characters",
                    phone,
                    f"Verify {party_type} phone number is correct"
                ))
                
        return errors, warnings
