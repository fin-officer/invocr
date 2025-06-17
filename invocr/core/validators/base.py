"""
Base validation classes and utilities for InvOCR
"""

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class ValidationError:
    """Represents a validation error"""

    field: str
    message: str
    severity: str  # 'error', 'warning', 'info'
    value: Any = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation result with errors and quality score"""

    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    errors: List[ValidationError]
    warnings: List[ValidationError]
    suggestions: List[str]

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class BaseValidator:
    """Base class for all validators"""
    
    def __init__(self):
        """Initialize the base validator"""
        pass
        
    def _create_error(self, field: str, message: str, value: Any = None, 
                     suggestion: Optional[str] = None) -> ValidationError:
        """Create a validation error"""
        return ValidationError(
            field=field,
            message=message,
            severity="error",
            value=value,
            suggestion=suggestion
        )
        
    def _create_warning(self, field: str, message: str, value: Any = None,
                       suggestion: Optional[str] = None) -> ValidationError:
        """Create a validation warning"""
        return ValidationError(
            field=field,
            message=message,
            severity="warning",
            value=value,
            suggestion=suggestion
        )
