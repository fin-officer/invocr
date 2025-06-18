"""
Adapter for valider package.

This module re-exports functionality from the valider package
to maintain backward compatibility with existing code.
"""

# Re-export validation functionality from valider
from valider.base import (
    Validator,
    FieldValidator, 
    DocumentValidator,
    ValidationResult,
    ValidationError
)

from valider.field_validators import (
    AmountValidator,
    DateValidator,
    TextValidator,
    TaxIDValidator,
    PercentageValidator,
    EmailValidator,
    PhoneValidator
)

from valider.document_validators import (
    InvoiceValidator,
    ReceiptValidator,
    BankStatementValidator
)

# For backward compatibility
from valider import *
