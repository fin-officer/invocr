"""
Data models for PDF processing
Contains dataclasses for invoice data representation
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


@dataclass
class Address:
    """Represents a postal address"""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ContactInfo:
    """Represents contact information"""
    name: str = ""
    email: str = ""
    phone: str = ""
    address: Address = field(default_factory=Address)
    tax_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['address'] = self.address.to_dict()
        return result


@dataclass
class PaymentInfo:
    """Represents payment information"""
    account_name: str = ""
    account_number: str = ""
    bank_name: str = ""
    routing_number: str = ""
    iban: str = ""
    swift: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class InvoiceItem:
    """Represents an invoice line item"""
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0
    currency: str = ""
    item_code: str = ""
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class InvoiceTotals:
    """Represents invoice totals"""
    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    discount: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    currency: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Invoice:
    """
    Represents an invoice document with all its components.
    """
    # Document identification
    document_number: str = ""
    document_type: str = "invoice"  # invoice, credit_note, debit_note, etc.
    
    # Dates
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    
    # Parties
    seller: ContactInfo = field(default_factory=ContactInfo)
    buyer: ContactInfo = field(default_factory=ContactInfo)
    
    # Document items
    items: List[InvoiceItem] = field(default_factory=list)
    
    # Totals
    totals: InvoiceTotals = field(default_factory=InvoiceTotals)
    
    # Payment information
    payment_terms: str = ""
    payment_info: PaymentInfo = field(default_factory=PaymentInfo)
    
    # Additional information
    notes: str = ""
    reference: str = ""
    
    # Metadata
    language: str = "en"
    currency: str = "USD"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the invoice to a dictionary.
        
        Returns:
            Dictionary representation of the invoice
        """
        result = asdict(self)
        
        # Convert datetime objects to ISO format strings
        for date_field in ['issue_date', 'due_date']:
            if date_value := getattr(self, date_field, None):
                result[date_field] = date_value.isoformat()
        
        # Convert nested objects to dictionaries
        result['seller'] = self.seller.to_dict()
        result['buyer'] = self.buyer.to_dict()
        result['items'] = [item.to_dict() for item in self.items]
        result['totals'] = self.totals.to_dict()
        result['payment_info'] = self.payment_info.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Invoice':
        """
        Create an Invoice instance from a dictionary.
        
        Args:
            data: Dictionary containing invoice data
            
        Returns:
            Invoice instance
        """
        # Create a copy to avoid modifying the input
        data = data.copy()
        
        # Handle nested objects
        if 'seller' in data:
            data['seller'] = ContactInfo(**data['seller'])
        if 'buyer' in data:
            data['buyer'] = ContactInfo(**data['buyer'])
        if 'items' in data:
            data['items'] = [InvoiceItem(**item) for item in data['items']]
        if 'totals' in data:
            data['totals'] = InvoiceTotals(**data['totals'])
        if 'payment_info' in data:
            data['payment_info'] = PaymentInfo(**data.get('payment_info', {}))
        
        # Handle date strings
        for date_field in ['issue_date', 'due_date']:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])
        
        return cls(**data)
