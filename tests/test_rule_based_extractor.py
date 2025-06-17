"""
Tests for the rule-based PDF extractor functionality.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, date
import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from invocr.formats.pdf.rule_based_extractor import RuleBasedExtractor
from invocr.formats.pdf.document_models import Invoice, Party, Address, InvoiceItem, PaymentTerms

def create_sample_extractor():
    """Create a sample rule-based extractor for testing."""
    return RuleBasedExtractor()

def test_extract_invoice_basic():
    """Test basic invoice extraction."""
    extractor = create_sample_extractor()
    
    # Sample invoice text
    text = """
    INVOICE #INV-2023-001
    Date: 2023-10-15
    Due Date: 2023-11-14
    
    From: Test Company Inc.
    123 Business St, City, Country
    VAT: GB123456789
    
    Bill To: Client Name
    456 Client Ave, Client City
    
    Description            Qty  Unit Price  Amount
    -----------------------------------------------
    Web Design Service     10    100.00      1000.00
    Hosting (1 year)       1     120.00      120.00
    
    Subtotal: 1120.00
    VAT (20%): 224.00
    Total: 1344.00
    
    Payment Terms: Net 30
    """
    
    # Extract invoice data
    result = extractor.extract_invoice(text)
    
    # Verify basic fields
    assert result.invoice_number == "INV-2023-001"
    assert result.issue_date == date(2023, 10, 15)
    assert result.due_date == date(2023, 11, 14)
    
    # Verify seller information
    assert result.seller.name == "Test Company Inc."
    assert "123 Business St" in result.seller.address.full_address
    
    # Verify buyer information
    assert result.buyer.name == "Client Name"
    
    # Verify items
    assert len(result.items) == 2
    assert result.items[0].description == "Web Design Service"
    assert result.items[0].quantity == 10
    assert result.items[0].unit_price == 100.0
    assert result.items[0].total_price == 1000.0
    
    # Verify totals
    assert result.subtotal == 1120.0
    assert result.tax_amount == 224.0
    assert result.total == 1344.0
    
    # Verify payment terms
    assert result.payment_terms.terms == "Net 30"

def test_extract_invoice_multicurrency():
    """Test invoice extraction with different currency formats."""
    extractor = create_sample_extractor()
    
    text = """
    INVOICE #INV-2023-002
    Date: 15.10.2023
    
    From: Euro Company
    
    Description       Qty  Unit Price  Amount
    ------------------------------------------
    Service 1         2     €100,50     €201,00
    Service 2         1     €75,25      €75,25
    
    Net: €276,25
    VAT (21%): €58,01
    Total: €334,26
    """
    
    result = extractor.extract_invoice(text)
    
    assert result.invoice_number == "INV-2023-002"
    assert result.issue_date == date(2023, 10, 15)
    assert len(result.items) == 2
    assert result.items[0].unit_price == 100.5
    assert result.items[1].unit_price == 75.25
    assert result.subtotal == 276.25
    assert abs(result.tax_amount - 58.01) < 0.01  # Allow for floating point precision
    assert abs(result.total - 334.26) < 0.01

def test_extract_invoice_different_date_formats():
    """Test extraction with various date formats."""
    extractor = create_sample_extractor()
    
    test_cases = [
        ("15.10.2023", date(2023, 10, 15)),
        ("15/10/2023", date(2023, 10, 15)),
        ("15-10-2023", date(2023, 10, 15)),
        ("2023-10-15", date(2023, 10, 15)),
        ("15 Oct 2023", date(2023, 10, 15)),
        ("15 October 2023", date(2023, 10, 15)),
        ("Oct 15, 2023", date(2023, 10, 15)),
    ]
    
    for date_str, expected_date in test_cases:
        text = f"""
        INVOICE #TEST-001
        Date: {date_str}
        Due Date: {date_str}
        
        From: Test
        To: Test
        
        Total: 100.00
        """
        
        result = extractor.extract_invoice(text)
        assert result.issue_date == expected_date
        assert result.due_date == expected_date

def test_extract_invoice_with_payment_terms():
    """Test extraction of various payment terms."""
    extractor = create_sample_extractor()
    
    test_cases = [
        ("Payment Terms: Net 30", "Net 30"),
        ("Zahlungsbedingungen: 14 Tage", "14 Tage"),
        ("Conditions de paiement: 30 jours", "30 jours"),
        ("Condiciones de pago: 30 días", "30 días"),
    ]
    
    for terms_text, expected_terms in test_cases:
        text = f"""
        INVOICE #TEST-002
        Date: 2023-10-15
        
        From: Test
        To: Test
        
        {terms_text}
        
        Total: 100.00
        """
        
        result = extractor.extract_invoice(text)
        assert result.payment_terms.terms == expected_terms

def test_extract_invoice_with_tax_calculation():
    """Test tax calculation from subtotal and total."""
    extractor = create_sample_extractor()
    
    text = """
    INVOICE #TAX-001
    Date: 2023-10-15
    
    From: Test
    To: Test
    
    Description    Qty  Unit Price  Amount
    ---------------------------------------
    Item 1         2     50.00      100.00
    Item 2         1     100.00     100.00
    
    Subtotal: 200.00
    VAT (20%): 40.00
    Total: 240.00
    """
    
    result = extractor.extract_invoice(text)
    
    assert len(result.items) == 2
    assert result.subtotal == 200.0
    assert result.tax_amount == 40.0
    assert result.tax_rate == 20.0
    assert result.total == 240.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
