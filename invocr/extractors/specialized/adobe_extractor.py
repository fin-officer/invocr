"""
Adobe invoice specialized extractor for improved data extraction from Adobe invoice PDFs.

This module provides a specialized extractor for Adobe invoices that implements
multi-level detection to improve accuracy of extracted data by comparing OCR text
with JSON data and applying specialized parsing for Adobe's invoice format.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import datetime
from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor
from invocr.formats.pdf.models import Invoice, InvoiceItem, Address, ContactInfo as Party


class AdobeInvoiceExtractor(BaseInvoiceExtractor):
    """Specialized extractor for Adobe invoice JSON data with OCR verification."""
    
    def __init__(self, ocr_text: str = None):
        super().__init__()
        self.ocr_text = ocr_text
        self.confidence_scores = {}
    
    def extract(self, json_data: Dict[str, Any]) -> Invoice:
        """Extract invoice data from Adobe JSON format with OCR verification."""
        invoice = Invoice()
        
        # Extract basic fields using multi-level detection
        invoice.invoice_number = self._extract_invoice_number(json_data)
        invoice.issue_date = self._extract_date(json_data)
        invoice.due_date = self._extract_due_date(json_data)
        invoice.currency = self._extract_currency(json_data)
        
        # Extract parties from mixed data
        buyer, seller = self._extract_parties(json_data)
        invoice.buyer = buyer
        invoice.seller = seller
        
        # Extract items from address field where they're incorrectly placed
        invoice.items = self._extract_items(json_data)
        
        # Extract and correct totals
        invoice.total_amount, invoice.tax_amount, invoice.subtotal = self._extract_corrected_totals(json_data)
        
        # Post-process and verify with OCR if available
        if self.ocr_text:
            self._verify_with_ocr(invoice)
            
        return invoice
    
    def _extract_invoice_number(self, data: Dict[str, Any]) -> str:
        """Extract invoice number with multiple detection strategies."""
        # Level 1: Try from transaction ID in filename
        filename = data.get("_metadata", {}).get("filename", "")
        if filename:
            match = re.search(r'Adobe_Transaction_No_(\d+)', filename)
            if match:
                return match.group(1)
        
        # Level 2: Try from PO number field
        if "po_number" in data and data["po_number"] not in ["", "Information"]:
            return data["po_number"]
            
        # Level 3: Try from payment terms where order number might be
        if "payment_terms" in data:
            match = re.search(r'Order Number\s+(\d+)', data["payment_terms"])
            if match:
                return match.group(1)
        
        # Level 4: Search in address fields where it might be mixed in
        seller_address = data.get("seller", {}).get("address", "")
        match = re.search(r'Order Number\s+(\d+)', seller_address)
        if match:
            return match.group(1)
            
        return ""
    
    def _extract_date(self, data: Dict[str, Any]) -> datetime:
        """Extract issue date from various locations in the document."""
        # Level 1: Look for service term in address or payment terms
        address = data.get("seller", {}).get("address", "")
        payment_terms = data.get("payment_terms", "")
        
        for text in [address, payment_terms]:
            match = re.search(r'Service Term:\s+(\d{2}-[A-Z]{3}-\d{4})\s+to', text)
            if match:
                try:
                    return datetime.strptime(match.group(1), "%d-%b-%Y")
                except ValueError:
                    pass
        
        # Level 2: Extract from filename
        filename = data.get("_metadata", {}).get("filename", "")
        if filename:
            match = re.search(r'_(\d{8})\.json$', filename)
            if match:
                try:
                    return datetime.strptime(match.group(1), "%Y%m%d")
                except ValueError:
                    pass
        
        return None
    
    def _extract_due_date(self, data: Dict[str, Any]) -> datetime:
        """Extract due date from service term end date."""
        address = data.get("seller", {}).get("address", "")
        payment_terms = data.get("payment_terms", "")
        
        for text in [address, payment_terms]:
            match = re.search(r'to\s+(\d{2}-[A-Z]{3}-\d{4})', text)
            if match:
                try:
                    return datetime.strptime(match.group(1), "%d-%b-%Y")
                except ValueError:
                    pass
        
        return None
    
    def _extract_currency(self, data: Dict[str, Any]) -> str:
        """Extract currency code from various locations."""
        # Level 1: Check direct field
        if "currency" in data and data["currency"] != "TAX":
            return data["currency"]
        
        # Level 2: Look in payment terms
        if "payment_terms" in data:
            match = re.search(r'Currency\s+([A-Z]{3})', data["payment_terms"])
            if match:
                return match.group(1)
        
        # Level 3: Look in address field where data is often mixed
        address = data.get("seller", {}).get("address", "")
        match = re.search(r'NET AMOUNT \(([A-Z]{3})\)', address)
        if match:
            return match.group(1)
            
        match = re.search(r'GRAND TOUAL \(([A-Z]{3})\)', address)
        if match:
            return match.group(1)
        
        return ""
    
    def _extract_parties(self, data: Dict[str, Any]) -> Tuple[Party, Party]:
        """Extract buyer and seller information correctly."""
        buyer = Party()
        seller = Party()
        
        # Extract buyer info from payment_terms which contains more accurate data
        payment_terms = data.get("payment_terms", "")
        
        # Extract buyer name and address
        bill_to_match = re.search(r'Bill To\s+(.*?)(?=\s+Customer VAT No:|$)', payment_terms, re.DOTALL)
        if bill_to_match:
            lines = bill_to_match.group(1).strip().split('\n')
            if lines:
                buyer.name = lines[0].strip()
                buyer.address = Address(street='\n'.join(lines[1:]).strip())
        
        # Extract buyer VAT number
        vat_match = re.search(r'Customer VAT No:\s+([A-Z0-9]+)', payment_terms)
        if vat_match:
            buyer.tax_id = vat_match.group(1)
        
        # Set seller info (Adobe is always the seller)
        seller.name = "Adobe"
        
        # Look for seller VAT in payment terms
        seller_vat_match = re.search(r'PayPal VAT No:\s+([A-Z0-9]+)', payment_terms)
        if seller_vat_match:
            seller.tax_id = seller_vat_match.group(1)
        
        return buyer, seller
    
    def _extract_items(self, data: Dict[str, Any]) -> List[InvoiceItem]:
        """Extract invoice items from address field where they're incorrectly placed."""
        items = []
        
        # The items are often in the address field or payment_terms
        text_sources = [
            data.get("seller", {}).get("address", ""),
            data.get("payment_terms", "")
        ]
        
        for source in text_sources:
            # First look for the item details section
            item_section_match = re.search(r'Item\]Details.*?Service Term:.*?(PRODUCT NUMBER.*?)(?:Invoice Total|$)', 
                                          source, re.DOTALL | re.IGNORECASE)
            
            if not item_section_match:
                continue
                
            item_section = item_section_match.group(1)
            
            # Extract individual items with regex pattern matching Adobe's format
            item_pattern = r'(\d+)\s+([\w\s]+)\s+(\d+)\s+([A-Z]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+%)\s+([\d.]+)\s+([\d.]+)'
            item_matches = re.finditer(item_pattern, item_section)
            
            for match in item_matches:
                item = InvoiceItem()
                item.product_code = match.group(1)
                item.description = match.group(2).strip()
                item.quantity = float(match.group(3))
                item.unit = match.group(4)
                item.unit_price = float(match.group(5))
                item.net_amount = float(match.group(6))
                # Extract tax rate percentage without the % symbol
                item.tax_rate = float(match.group(7).rstrip('%'))
                item.tax_amount = float(match.group(8))
                item.total_amount = float(match.group(9))
                
                items.append(item)
        
        return items
    
    def _extract_corrected_totals(self, data: Dict[str, Any]) -> Tuple[float, float, float]:
        """Extract and correct invoice totals."""
        total_amount = 0.0
        tax_amount = 0.0
        subtotal = 0.0
        
        # Look in address and payment_terms for totals
        text_sources = [
            data.get("seller", {}).get("address", ""),
            data.get("payment_terms", "")
        ]
        
        for source in text_sources:
            # Extract net amount (subtotal)
            net_match = re.search(r'NET AMOUNT\s+\([A-Z]{3}\)\s+([\d.]+)', source)
            if net_match:
                subtotal = float(net_match.group(1))
            
            # Extract taxes
            tax_match = re.search(r'TAXES[^)]+\s+([\d.]+)', source)
            if tax_match:
                tax_amount = float(tax_match.group(1))
            
            # Extract grand total
            total_match = re.search(r'GRAND TOUAL[^)]+\s+([\d.]+)', source)
            if total_match:
                total_amount = float(total_match.group(1))
        
        # If we couldn't extract the totals, calculate from items
        if total_amount == 0.0 and subtotal == 0.0:
            items = self._extract_items(data)
            if items:
                subtotal = sum(item.net_amount for item in items)
                tax_amount = sum(item.tax_amount for item in items)
                total_amount = sum(item.total_amount for item in items)
        
        return total_amount, tax_amount, subtotal
    
    def _verify_with_ocr(self, invoice: Invoice) -> None:
        """Compare extracted data with OCR text to improve confidence."""
        if not self.ocr_text:
            return
            
        confidence_scores = {}
        
        # Check invoice number
        if invoice.invoice_number and invoice.invoice_number in self.ocr_text:
            confidence_scores["invoice_number"] = 1.0
        else:
            confidence_scores["invoice_number"] = 0.5
        
        # Check currency
        if invoice.currency and invoice.currency in self.ocr_text:
            confidence_scores["currency"] = 1.0
        else:
            confidence_scores["currency"] = 0.5
        
        # Check totals
        total_str = f"{invoice.total_amount:.2f}"
        if total_str in self.ocr_text:
            confidence_scores["total_amount"] = 1.0
        else:
            confidence_scores["total_amount"] = 0.5
            
        # Check item descriptions
        item_confidence = []
        for item in invoice.items:
            if item.description and item.description in self.ocr_text:
                item_confidence.append(1.0)
            else:
                item_confidence.append(0.5)
                
        if item_confidence:
            confidence_scores["items"] = sum(item_confidence) / len(item_confidence)
        
        # Store confidence scores
        self.confidence_scores = confidence_scores
