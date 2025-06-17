"""
Document validation module for InvOCR
Validates document numbers and dates
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from .base import BaseValidator, ValidationError

class DocumentValidator(BaseValidator):
    """Validator for document numbers and dates"""
    
    def __init__(self):
        """Initialize the document validator"""
        super().__init__()
        
    def validate_document_number(self, document_number: str) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Validate document number format and content
        
        Args:
            document_number: Document number to validate
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check if empty
        if not document_number:
            errors.append(self._create_error(
                "document_number", 
                "Document number is empty",
                document_number
            ))
            return errors, warnings
            
        # Check if too short
        if len(document_number) < 3:
            warnings.append(self._create_warning(
                "document_number",
                "Document number is unusually short",
                document_number,
                "Verify document number is complete"
            ))
            
        # Check if too long
        if len(document_number) > 30:
            warnings.append(self._create_warning(
                "document_number",
                "Document number is unusually long",
                document_number,
                "Verify document number is correct"
            ))
            
        # Check if contains invalid characters
        if re.search(r'[^A-Za-z0-9\-_/\.]', document_number):
            warnings.append(self._create_warning(
                "document_number",
                "Document number contains unusual characters",
                document_number,
                "Verify document number is correct"
            ))
            
        return errors, warnings
        
    def validate_dates(self, data: Dict[str, Any]) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Validate document dates (issue date, due date)
        
        Args:
            data: Invoice data dictionary
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        issue_date = data.get("issue_date")
        due_date = data.get("due_date")
        
        # Check issue date
        if issue_date:
            try:
                # Check if date is in the future
                issue_date_obj = datetime.strptime(issue_date, "%Y-%m-%d")
                if issue_date_obj > datetime.now() + timedelta(days=1):
                    warnings.append(self._create_warning(
                        "issue_date",
                        "Issue date is in the future",
                        issue_date,
                        "Verify issue date is correct"
                    ))
                    
                # Check if date is too far in the past
                if issue_date_obj < datetime.now() - timedelta(days=365*5):
                    warnings.append(self._create_warning(
                        "issue_date",
                        "Issue date is more than 5 years in the past",
                        issue_date,
                        "Verify issue date is correct"
                    ))
            except (ValueError, TypeError):
                errors.append(self._create_error(
                    "issue_date",
                    "Invalid issue date format, expected YYYY-MM-DD",
                    issue_date,
                    "Format date as YYYY-MM-DD"
                ))
                
        # Check due date
        if due_date:
            try:
                # Check if date is valid
                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                
                # Check if due date is before issue date
                if issue_date and not isinstance(issue_date_obj, type(None)):
                    if due_date_obj < issue_date_obj:
                        errors.append(self._create_error(
                            "due_date",
                            "Due date is before issue date",
                            due_date,
                            "Due date must be on or after issue date"
                        ))
                        
                # Check if due date is too far in the future
                if due_date_obj > datetime.now() + timedelta(days=365):
                    warnings.append(self._create_warning(
                        "due_date",
                        "Due date is more than 1 year in the future",
                        due_date,
                        "Verify due date is correct"
                    ))
            except (ValueError, TypeError):
                errors.append(self._create_error(
                    "due_date",
                    "Invalid due date format, expected YYYY-MM-DD",
                    due_date,
                    "Format date as YYYY-MM-DD"
                ))
                
        return errors, warnings
