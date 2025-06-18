"""
Unit tests for the Adobe invoice specialized extractor.
"""
import os
import json
from datetime import datetime
import pytest
from invocr.extractors.specialized.adobe_extractor import AdobeInvoiceExtractor

# Test data paths
SAMPLE_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'invoices_json', 'Adobe_Transaction_No_2860733415_20240901.json')


def load_sample_json():
    """Load sample Adobe invoice JSON file for testing."""
    if not os.path.exists(SAMPLE_JSON_PATH):
        pytest.skip(f"Sample JSON file not found: {SAMPLE_JSON_PATH}")
    
    with open(SAMPLE_JSON_PATH, 'r') as f:
        return json.load(f)


def test_adobe_extractor_initialization():
    """Test that the Adobe extractor initializes correctly."""
    extractor = AdobeInvoiceExtractor()
    assert extractor is not None


def test_extract_invoice_number():
    """Test extracting invoice number from Adobe JSON."""
    json_data = load_sample_json()
    extractor = AdobeInvoiceExtractor()
    
    # Update the json_data to include a filename in metadata
    if "_metadata" not in json_data:
        json_data["_metadata"] = {}
    json_data["_metadata"]["filename"] = "Adobe_Transaction_No_2860733415_20240901.json"
    
    invoice = extractor.extract(json_data)
    assert invoice.invoice_number == "2860733415"


def test_extract_currency():
    """Test extracting currency from Adobe JSON."""
    json_data = load_sample_json()
    extractor = AdobeInvoiceExtractor()
    
    invoice = extractor.extract(json_data)
    assert invoice.currency == "EUR"


def test_extract_items():
    """Test extracting invoice items from Adobe JSON."""
    json_data = load_sample_json()
    extractor = AdobeInvoiceExtractor()
    
    invoice = extractor.extract(json_data)
    assert len(invoice.items) > 0
    
    # Verify first item details (InDesign product)
    item = invoice.items[0]
    assert item.product_code == "65183246"
    assert "InDesign" in item.description
    assert item.quantity == 1.0
    assert item.unit == "EA"
    assert item.unit_price == 21.84
    assert item.net_amount == 21.84
    assert item.tax_rate == 0.0
    assert item.tax_amount == 0.0
    assert item.total_amount == 21.84


def test_extract_totals():
    """Test extracting and correcting totals from Adobe JSON."""
    json_data = load_sample_json()
    extractor = AdobeInvoiceExtractor()
    
    invoice = extractor.extract(json_data)
    
    # Based on the sample data, the expected totals are:
    assert invoice.subtotal == 21.84
    assert invoice.tax_amount == 0.0
    assert invoice.total_amount == 21.84


def test_extract_dates():
    """Test extracting dates from Adobe JSON."""
    json_data = load_sample_json()
    extractor = AdobeInvoiceExtractor()
    
    invoice = extractor.extract(json_data)
    
    # Based on the sample data, the expected dates are:
    assert invoice.issue_date.date() == datetime(2024, 8, 31).date()
    assert invoice.due_date.date() == datetime(2024, 9, 29).date()


def test_extract_buyer_seller():
    """Test extracting buyer and seller information from Adobe JSON."""
    json_data = load_sample_json()
    extractor = AdobeInvoiceExtractor()
    
    invoice = extractor.extract(json_data)
    
    # Verify seller (Adobe)
    assert invoice.seller.name == "Adobe"
    assert invoice.seller.tax_id == "IE6364992H"
    
    # Verify buyer (extracted from payment_terms)
    assert "Tomasz" in invoice.buyer.name
    assert "TALLINN" in invoice.buyer.address.street
    assert invoice.buyer.tax_id == "EE102146710"
