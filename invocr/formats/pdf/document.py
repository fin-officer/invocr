"""
Document models for PDF processing.

This module defines the core data structures used for representing
extracted invoice data in a structured format.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
import re


@dataclass
class Address:
    """Represents a physical or mailing address."""
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    raw: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'street': self.street,
            'city': self.city,
            'postal_code': self.postal_code,
            'country': self.country,
            'raw': self.raw
        }


@dataclass
class Party:
    """Represents a party (buyer or seller) in an invoice."""
    name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[Address] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    registration_number: Optional[str] = None
    vat_number: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'tax_id': self.tax_id,
            'address': self.address.to_dict() if self.address else None,
            'email': self.email,
            'phone': self.phone,
            'registration_number': self.registration_number,
            'vat_number': self.vat_number
        }


@dataclass
class InvoiceItem:
    """Represents a line item in an invoice."""
    description: str
    quantity: float = 1.0
    unit_price: Optional[Decimal] = None
    unit: Optional[str] = None
    net_amount: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    item_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'description': self.description,
            'quantity': float(self.quantity) if self.quantity else None,
            'unit_price': float(self.unit_price) if self.unit_price else None,
            'unit': self.unit,
            'net_amount': float(self.net_amount) if self.net_amount else None,
            'tax_rate': float(self.tax_rate) if self.tax_rate else None,
            'tax_amount': float(self.tax_amount) if self.tax_amount else None,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'item_code': self.item_code
        }


@dataclass
class PaymentTerms:
    """Represents payment terms for an invoice."""
    due_date: Optional[date] = None
    terms: Optional[str] = None
    discount_days: Optional[int] = None
    discount_amount: Optional[Decimal] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'terms': self.terms,
            'discount_days': self.discount_days,
            'discount_amount': float(self.discount_amount) if self.discount_amount else None
        }


@dataclass
class Invoice:
    """Represents an extracted invoice."""
    # Core fields
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    
    # Parties
    seller: Party = field(default_factory=Party)
    buyer: Party = field(default_factory=Party)
    
    # Financials
    currency: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    amount_due: Optional[Decimal] = None
    
    # Line items
    items: List[InvoiceItem] = field(default_factory=list)
    
    # Payment details
    payment_terms: PaymentTerms = field(default_factory=PaymentTerms)
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    
    # Additional metadata
    notes: List[str] = field(default_factory=list)
    reference_numbers: List[str] = field(default_factory=list)
    purchase_order: Optional[str] = None
    
    # Processing metadata
    confidence: Optional[float] = None
    extraction_method: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'seller': self.seller.to_dict() if self.seller else None,
            'buyer': self.buyer.to_dict() if self.buyer else None,
            'currency': self.currency,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else None,
            'subtotal': float(self.subtotal) if self.subtotal else None,
            'tax_amount': float(self.tax_amount) if self.tax_amount else None,
            'discount_amount': float(self.discount_amount) if self.discount_amount else None,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'amount_paid': float(self.amount_paid) if self.amount_paid else None,
            'amount_due': float(self.amount_due) if self.amount_due else None,
            'items': [item.to_dict() for item in self.items],
            'payment_terms': self.payment_terms.to_dict() if self.payment_terms else None,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'notes': self.notes,
            'reference_numbers': self.reference_numbers,
            'purchase_order': self.purchase_order,
            'confidence': self.confidence,
            'extraction_method': self.extraction_method,
            'raw_data': self.raw_data
        }
