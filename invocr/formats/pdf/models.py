"""
Data models for PDF processing
Contains dataclasses for invoice data representation
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class InvoiceItem:
    """Represents an invoice line item"""

    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0
    currency: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class InvoiceTotals:
    """Represents invoice totals"""

    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    currency: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
