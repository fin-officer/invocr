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
    
    def extract_invoice_data(self, text: str, document_type: str = "invoice", **kwargs) -> Dict[str, Any]:
        """
        Extract invoice data from text content. This is the main interface method expected by the converter.
        
        Args:
            text: OCR or direct text extracted from the document
            document_type: Type of document (invoice, receipt, etc.)
            
        Returns:
            Dictionary containing structured invoice data
        """
        print(f"\n=== Adobe Invoice Extractor processing {document_type} ===\n")
        
        # Create a mock JSON structure for Adobe invoice format
        # In a real scenario, this would come from PDF.js JSON extraction
        json_data = self._create_json_from_text(text)
        
        # Use the specialized extraction logic
        invoice = self.extract(json_data)
        
        # Convert Invoice object to dictionary for the expected interface
        return invoice.to_dict()
    
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
        total, tax_amount, subtotal = self._extract_corrected_totals(json_data)
        invoice.total_amount = total
        invoice.tax_amount = tax_amount
        invoice.subtotal = subtotal
        
        # Populate totals in the invoice.totals structure for JSON output
        invoice.totals.subtotal = subtotal
        invoice.totals.tax_amount = tax_amount
        invoice.totals.total = total
        
        # Set tax rate if available from items
        if len(invoice.items) > 0 and hasattr(invoice.items[0], 'tax_rate'):
            invoice.totals.tax_rate = invoice.items[0].tax_rate
        
        # Post-process and verify with OCR if available
        if self.ocr_text:
            self._verify_with_ocr(invoice)
        
        # Final verification: ensure totals are consistent with items
        self._verify_totals_consistency(invoice)
            
        return invoice
        
    def _create_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Create a structured JSON representation from plain text for Adobe invoices.
        
        Args:
            text: Plain text from the invoice (OCR or extracted)
            
        Returns:
            Dictionary with structured data in Adobe JSON format
        """
        json_data = {
            "invoice_number": "",
            "issue_date": "",
            "due_date": "",
            "currency": "",
            "buyer": {
                "name": "",
                "address": "",
                "tax_id": ""
            },
            "seller": {
                "name": "",
                "address": "",
                "tax_id": ""
            },
            "payment_terms": ""
        }
        
        # Extract invoice number
        invoice_number_match = re.search(r"Invoice\s+Number\s+([\w-]+)", text, re.IGNORECASE)
        if invoice_number_match:
            json_data["invoice_number"] = invoice_number_match.group(1)
        
        # Extract date
        date_match = re.search(r"Invoice\s+Date\s+(\d{1,2}-[A-Z]{3}-\d{4})", text, re.IGNORECASE)
        if date_match:
            json_data["issue_date"] = date_match.group(1)
        
        # Extract currency
        currency_match = re.search(r"Currency\s+([A-Z]{3})", text, re.IGNORECASE)
        if currency_match:
            json_data["currency"] = currency_match.group(1)
        
        # Extract payment terms
        payment_terms_match = re.search(r"Payment\s+Terms\s+(.+?)\s+VAT\s+No", text, re.IGNORECASE | re.DOTALL)
        if payment_terms_match:
            json_data["payment_terms"] = payment_terms_match.group(1).strip()
        
        # Copy the full text to seller address for item extraction (Adobe's format quirk)
        json_data["seller"]["address"] = text
        
        # Extract seller name
        seller_match = re.search(r"(Adobe\s+Systems\s+Software\s+Ireland\s+Ltd)", text, re.IGNORECASE)
        if seller_match:
            json_data["seller"]["name"] = seller_match.group(1)
            
        # Extract buyer name and address
        buyer_match = re.search(r"Bill\s+To\s+(.+?)\s+Customer\s+VAT\s+No", text, re.IGNORECASE | re.DOTALL)
        if buyer_match:
            buyer_text = buyer_match.group(1).strip()
            lines = buyer_text.split("\n")
            if lines:
                json_data["buyer"]["name"] = lines[0].strip()
                json_data["buyer"]["address"] = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        
        # Extract tax IDs
        seller_vat_match = re.search(r"VAT\s+No:\s+([A-Z0-9]+)", text, re.IGNORECASE)
        if seller_vat_match:
            json_data["seller"]["tax_id"] = seller_vat_match.group(1)
            
        buyer_vat_match = re.search(r"Customer\s+VAT\s+No:\s+([A-Z0-9]+)", text, re.IGNORECASE)
        if buyer_vat_match:
            json_data["buyer"]["tax_id"] = buyer_vat_match.group(1)
        
        return json_data
    
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
        
        # Look for standard invoice number format with enhanced refund/credit patterns
        invoice_patterns = [
            # Standard invoice patterns
            r'Invoice\s+Number\s+([\w\-]+)',
            r'Invoice\s+#\s*([\w\-]+)',
            r'INV([\w\-]+)',
            
            # Credit note and refund patterns
            r'Credit\s+Note\s+Number\s*[:#]?\s*([\w\-]+)',
            r'Credit\s+Note\s+#\s*([\w\-]+)',
            r'Credit\s+#\s*([\w\-]+)',
            r'Refund\s+Number\s*[:#]?\s*([\w\-]+)',
            r'Refund\s+#\s*([\w\-]+)',
            r'Reference\s+Number\s*[:#]?\s*([\w\-]+)',
            r'Reference\s+#\s*([\w\-]+)',
            r'Transaction\s+ID\s*[:#]?\s*([\w\-]+)',
            r'Transaction\s+Number\s*[:#]?\s*([\w\-]+)',
            r'Document\s+Number\s*[:#]?\s*([\w\-]+)',
            
            # Adobe-specific patterns
            r'Adobe\s+Document\s+ID\s*[:#]?\s*([\w\-]+)',
            r'Adobe\s+Transaction\s+ID\s*[:#]?\s*([\w\-]+)',
            r'CR([\w\-]+)'  # Credit note abbreviation pattern
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, seller_address, re.IGNORECASE)
            if match:
                return match.group(1)
                
        # Level 5: Look for any alphanumeric sequence that looks like an invoice number
        # This is a fallback for refund documents that might use different terminology
        fallback_patterns = [
            r'\b([A-Z0-9]{6,})\b',  # Alphanumeric sequence of 6+ characters
            r'\b(\d{4,}-\d{4,})\b',  # Number-dash-number pattern
            r'\b(CR-\d+)\b'  # CR-number pattern
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, seller_address, re.IGNORECASE)
            if matches:
                # Filter out common false positives
                filtered_matches = [m for m in matches 
                                  if not re.match(r'\d{1,2}-\d{1,2}-\d{4}', m)  # Not a date
                                  and not re.match(r'\d{5,}', m)  # Not a long number (e.g. phone)
                                  and m not in ['000000', 'FFFFFF']]  # Not placeholder values
                if filtered_matches:
                    return filtered_matches[0]
                
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
        
        # Add OCR text as a source if available
        if self.ocr_text:
            text_sources.append(self.ocr_text)
        
        print(f"\n=== Looking for items in {len(text_sources)} sources ===\n")
        
        for i, source in enumerate(text_sources):
            print(f"Searching source {i+1} for items:")
            if not source:
                print("  Source is empty, skipping")
                continue
                
            # First try to find the item details section using multiple patterns
            item_section_patterns = [
                # Various item section header patterns
                r'(?:Item|ITEM)\]?\s*Details.*?Service Term:.*?(PRODUCT\s*NUMBER.*?)(?:Invoice Total|$)',
                r'(?:PRODUCT\s*NUMBER).*?(\d+\s+[\w\s]+\s+\d+\s+[A-Z]{2}\s+[\d.]+\s+[\d.]+)',
                r'(\d+\s+[\w\s]+\s+\d+\s+EA\s+[\d.]+\s+[\d.]+)',
            ]
            
            item_section = None
            pattern_used = None
            
            for pattern in item_section_patterns:
                item_section_match = re.search(pattern, source, re.DOTALL | re.IGNORECASE)
                if item_section_match:
                    item_section = item_section_match.group(1)
                    pattern_used = pattern
                    print(f"  ✓ Found item section using pattern: {pattern[:30]}...")
                    print(f"  Item section snippet: {item_section[:50]}...")
                    break
            
            if not item_section:
                print("  ✗ No item section found in this source")
                continue
                
            # Extract individual items with regex patterns, trying multiple formats
            item_patterns = [
                # Full Adobe invoice format with all columns
                r'(\d+)\s+([\w\s]+)\s+(\d+)\s+([A-Z]{2})\s+([\d.,\(\)\-]+)\s+([\d.,\(\)\-]+)\s+([\d.,]+%)\s+([\d.,\(\)\-]+)\s+([\d.,\(\)\-]+)',
                
                # Simplified format with fewer columns
                r'(\d+)\s+([\w\s]+)\s+(\d+)\s+([A-Z]{2})\s+([\d.,\(\)\-]+)\s+([\d.,\(\)\-]+)',
                
                # Format for OCR text that might be misaligned
                r'([\d]+)\s+([\w\s]+?)\s+([\d]+)\s+([A-Z]{2})\s+([\d.,\(\)\-]+)\s+([\d.,\(\)\-]+)',
                
                # Format for refund items with negative values
                r'(\d+)\s+([\w\s]+)\s+(\d+)\s+([A-Z]{2})\s+\(([\d.,]+)\)\s+\(([\d.,]+)\)',
                
                # Format for credit items with negative values
                r'(\d+)\s+([\w\s]+Credit[\w\s]*)\s+(\d+)\s+([A-Z]{2})\s+([\d.,]+)\s+([\d.,]+)'
            ]
            
            items_found = False
            
            for pattern_idx, pattern in enumerate(item_patterns):
                item_matches = list(re.finditer(pattern, item_section, re.IGNORECASE))
                if item_matches:
                    print(f"  ✓ Found {len(item_matches)} items using pattern {pattern_idx+1}")
                    items_found = True
                    
                    for match_idx, match in enumerate(item_matches):
                        try:
                            item = InvoiceItem()
                            item.product_code = match.group(1).strip()
                            item.item_code = match.group(1).strip()  # Map product_code to item_code for JSON output
                            item.description = match.group(2).strip()
                            item.quantity = float(match.group(3).strip())
                            item.unit = match.group(4).strip()
                            # Parse unit price, handling negative values and parentheses
                            unit_price_str = match.group(5).strip()
                            item.unit_price = self._parse_amount(unit_price_str)
                            
                            # Set currency from invoice data
                            item.currency = self._extract_currency(data) or "EUR"  # Default to EUR for Adobe
                            
                            # Handle different pattern formats
                            if len(match.groups()) >= 6:
                                net_amount_str = match.group(6).strip()
                                item.net_amount = self._parse_amount(net_amount_str)
                                
                                # Check if this is a refund/credit item
                                is_refund = ('credit' in item.description.lower() or 
                                            unit_price_str.startswith('(') or 
                                            unit_price_str.startswith('-') or
                                            net_amount_str.startswith('(') or 
                                            net_amount_str.startswith('-'))
                                
                                # Ensure refund amounts are negative
                                if is_refund and item.net_amount > 0:
                                    item.net_amount = -item.net_amount
                                    if item.unit_price > 0:
                                        item.unit_price = -item.unit_price
                            
                            # Handle tax rate and tax amount if available (in full format)
                            if len(match.groups()) >= 8:
                                tax_rate_str = match.group(7).strip().rstrip('%')
                                item.tax_rate = float(tax_rate_str.replace(',', '.'))
                                tax_amount_str = match.group(8).strip()
                                item.tax_amount = self._parse_amount(tax_amount_str)
                                
                                # Ensure tax amount sign matches net amount for refunds
                                if item.net_amount < 0 and item.tax_amount > 0:
                                    item.tax_amount = -item.tax_amount
                            else:
                                item.tax_rate = 0.0
                                item.tax_amount = 0.0
                                
                            # Handle total amount if available, otherwise compute it
                            if len(match.groups()) >= 9:
                                total_amount_str = match.group(9).strip()
                                item.total_amount = self._parse_amount(total_amount_str)
                            else:
                                item.total_amount = item.net_amount + item.tax_amount
                                
                            # Set item.total field (used in JSON output)
                            item.total = item.total_amount
                            
                            # Ensure net_amount is set for all items
                            if not hasattr(item, 'net_amount') or item.net_amount is None:
                                item.net_amount = item.unit_price * item.quantity
                                
                            # For refund items, ensure all amounts are negative
                            if 'credit' in item.description.lower() or item.unit_price < 0:
                                if item.unit_price > 0:
                                    item.unit_price = -item.unit_price
                                if item.net_amount > 0:
                                    item.net_amount = -item.net_amount
                                if item.total_amount > 0:
                                    item.total_amount = -item.total_amount
                                if item.total > 0:
                                    item.total = -item.total
                                
                            items.append(item)
                            print(f"    Item {match_idx+1}: {item.description} - {item.quantity} {item.unit} x {item.unit_price} = {item.total_amount} (net: {item.net_amount})")
                        except Exception as e:
                            print(f"    Error parsing item {match_idx+1}: {e}")
                            continue
                    
                    # Break after finding items with any pattern
                    break
                    
            if not items_found:
                print("  ✗ No items matched in the section")
                            
        # Deduplicate items based on description, quantity, and unit price
        deduplicated_items = []
        seen_items = set()  # Track seen items using a tuple of (description, quantity, unit_price)
        
        for item in items:
            # Create a unique identifier for this item
            item_key = (item.description.strip(), item.quantity, item.unit_price)
            
            # Only add the item if we haven't seen it before
            if item_key not in seen_items:
                seen_items.add(item_key)
                deduplicated_items.append(item)
                
        if len(deduplicated_items) < len(items):
            print(f"  Removed {len(items) - len(deduplicated_items)} duplicate items")
            
        print(f"\n=== Extracted {len(deduplicated_items)} unique items total ===\n")
        return deduplicated_items
        
    def _verify_language(self, text: str) -> str:
        """Verify document language from text content using characteristic patterns.
        
        Args:
            text: Text content to analyze
            
        Returns:
            ISO language code ('en', 'et', etc.)
        """
        # Check for Adobe invoice specific phrases that indicate English
        adobe_patterns = [
            r'Adobe Systems Software Ireland',
            r'Invoice Information',
            r'Invoice Number',
            r'Invoice Date',
            r'Payment Terms',
            r'Purchase Order',
            r'PRODUCT DESCRIPTION',
            r'GRAND TO[TU]AL',  # Handles both TOTAL and TOUAL typo
        ]
        
        # Count matches for Adobe's English patterns
        english_score = sum(1 for pattern in adobe_patterns if re.search(pattern, text, re.IGNORECASE))
        
        # Check for Estonian specific patterns
        estonian_patterns = [
            r'TALLINN',
            r'Pärnu',
            r'EESTI|ESTONIA'
        ]
        estonian_score = sum(1 for pattern in estonian_patterns if re.search(pattern, text, re.IGNORECASE))
        
        print(f"Language verification scores - English: {english_score}, Estonian: {estonian_score}")
        
        # If we have strong Adobe English patterns, ensure we use English extractor
        if english_score >= 3:
            return 'en'
        elif estonian_score > english_score:
            return 'et'
        else:
            return 'en'  # Default to English for Adobe invoices
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string handling negative values and parentheses notation.
        
        Args:
            amount_str: String representation of an amount
            
        Returns:
            Float value of the amount, negative if in parentheses or with minus sign
        """
        if not amount_str or amount_str.strip() in ['(', ')', '-']:
            return 0.0
            
        # Remove any currency symbols or extra spaces
        clean_str = amount_str.replace(' ', '').strip()
        
        # Handle parentheses notation (accounting standard for negative values)
        if clean_str.startswith('(') and clean_str.endswith(')'):
            clean_str = '-' + clean_str[1:-1]
        
        # Replace commas with periods for decimal parsing
        clean_str = clean_str.replace(',', '.')
        
        try:
            return float(clean_str)
        except ValueError as e:
            print(f"Error parsing amount '{amount_str}': {e}")
            return 0.0
    
    def _extract_corrected_totals(self, data: Dict[str, Any]) -> Tuple[float, float, float]:
        """Extract and correct invoice totals from the data.
        
        Returns:
            Tuple of (total_amount, tax_amount, subtotal)
        """
        total_amount = 0.0
        tax_amount = 0.0
        subtotal = 0.0
        
        # The totals are often in the address field
        text_sources = [
            data.get("seller", {}).get("address", ""),
            data.get("payment_terms", "")
        ]
        
        # Add OCR text as a source if available
        if self.ocr_text:
            text_sources.append(self.ocr_text)
            
        print(f"\n=== Looking for totals in {len(text_sources)} sources ===\n")
        
        for i, source in enumerate(text_sources):
            print(f"Searching source {i+1}:")
            if not source:
                continue
                
            # Try to find the Invoice Total section first to ensure we're looking in the right place
            invoice_total_section_match = re.search(r'Invoice\s+Total.*?(?:GRAND\s+TO[TU]AL|$)', 
                                                   source, re.IGNORECASE | re.DOTALL)
                
            if invoice_total_section_match:
                invoice_total_section = invoice_total_section_match.group(0)
                print(f"  ✓ Found Invoice Total section")
            else:
                invoice_total_section = source  # Fallback to full source if section not found
            
            # Extract subtotal (NET AMOUNT)
            subtotal_patterns = [
                r'NET\s+AMOUNT\s*\(?[A-Z]{3}\)?\s*([\d.,\(\)\-]+)',
                r'NET\s+AMOUNT.*?([\d.,\(\)\-]+)\s',
                r'SubTotal\s*[:\s]\s*([\d.,\(\)\-]+)',
                r'CREDIT.*?AMOUNT.*?([\d.,\(\)\-]+)'
            ]
            
            for pattern in subtotal_patterns:
                subtotal_match = re.search(pattern, invoice_total_section, re.IGNORECASE)
                if subtotal_match:
                    try:
                        subtotal = self._parse_amount(subtotal_match.group(1))
                        print(f"  ✓ Subtotal found: {subtotal} using pattern: {pattern}")
                        break
                    except ValueError:
                        continue
            
            # Extract tax amount - make sure we're not capturing product codes
            tax_patterns = [
                r'TAXES\s*(?:\(SEE\s+DETAILS\s+FOR\s+RATES\)|\(?[A-Z]{3}\)?)?\s*([\d.,]+)',
                r'VAT\s*(?:AMOUNT)?\s*:?\s*([\d.,]+)',
                r'TAX\s*(?:AMOUNT)?\s*:?\s*([\d.,]+)'
            ]
            
            for pattern in tax_patterns:
                tax_match = re.search(pattern, invoice_total_section, re.IGNORECASE)
                if tax_match:
                    try:
                        tax_amount = self._parse_amount(tax_match.group(1))
                        print(f"  ✓ Tax amount found: {tax_amount} using pattern: {pattern}")
                        break
                    except ValueError:
                        continue
            
            # Extract total amount - look for "GRAND TOTAL" or variations
            # Make sure we're looking after "Invoice Total" to avoid picking up line items
            total_patterns = [
                r'GRAND\s+TO[TU]AL.*?\(?[A-Z]{3}\)?\s*([\d.,\(\)\-]+)', # Matches GRAND TOTAL and GRAND TOUAL
                r'TOTAL\s*AMOUNT\s*(?:\(?[A-Z]{3}\)?)?\s*([\d.,\(\)\-]+)',
                r'Invoice\s+Total.*?GRAND.*?([\d.,\(\)\-]+)',
                r'CREDIT.*?TOTAL.*?([\d.,\(\)\-]+)',
                r'NET\s+AMOUNT.*?([\d.,\(\)\-]+)', # Fallback to NET AMOUNT if total not found
                r'TOTAL.*?:\s*([\d.,\(\)\-]+)'
            ]
            
            for pattern in total_patterns:
                total_match = re.search(pattern, invoice_total_section, re.IGNORECASE)
                if total_match:
                    try:
                        total_amount = self._parse_amount(total_match.group(1))
                        print(f"  ✓ Total amount found: {total_amount} using pattern: {pattern}")
                        break
                    except ValueError:
                        continue
                    
            # If we found values in this source, no need to check others
            if subtotal > 0 and total_amount > 0:
                break
                tax_amount = sum(item.tax_amount for item in items if hasattr(item, 'tax_amount') and item.tax_amount is not None)
                total_amount = sum(item.total_amount for item in items if hasattr(item, 'total_amount') and item.total_amount is not None)
                print(f"  Calculated totals from {len(items)} items: Subtotal={subtotal}, Tax={tax_amount}, Total={total_amount}")
            else:
                print("  No items found to calculate totals")
        
        print(f"\n=== Final totals: Subtotal={subtotal}, Tax={tax_amount}, Total={total_amount} ===\n")
        
        # If we have items and they're all refunds/credits, ensure totals are negative
        items = self._extract_items(data)
        if items and all(item.unit_price < 0 or 'credit' in item.description.lower() for item in items):
            print("  All items are refunds/credits, ensuring totals are negative")
            if subtotal > 0:
                subtotal = -subtotal
            if tax_amount > 0:
                tax_amount = -tax_amount
            if total_amount > 0:
                total_amount = -total_amount
        
        return total_amount, tax_amount, subtotal
        
    def _verify_totals_consistency(self, invoice: Invoice) -> None:
        """Ensure totals are consistent with items and handle refund cases."""
        # If we have items but no totals, calculate from items
        if invoice.items and (invoice.total_amount == 0 or invoice.subtotal == 0):
            print("Recalculating totals from items")
            
            # Check if this is a refund invoice (all items negative)
            is_refund = all(getattr(item, 'unit_price', 0) < 0 or 
                           'credit' in getattr(item, 'description', '').lower() 
                           for item in invoice.items)
            
            # Calculate subtotal from items
            subtotal = sum(getattr(item, 'net_amount', 0) for item in invoice.items)
            tax_amount = sum(getattr(item, 'tax_amount', 0) for item in invoice.items)
            total = sum(getattr(item, 'total_amount', 0) for item in invoice.items)
            
            # If calculated total is zero but we have items, use net_amount + tax_amount
            if total == 0 and subtotal != 0:
                total = subtotal + tax_amount
                
            # For refund invoices, ensure totals are negative
            if is_refund:
                if subtotal > 0:
                    subtotal = -subtotal
                if tax_amount > 0:
                    tax_amount = -tax_amount
                if total > 0:
                    total = -total
            
            # Update invoice totals
            if invoice.subtotal == 0:
                invoice.subtotal = subtotal
                invoice.totals.subtotal = subtotal
                
            if invoice.tax_amount == 0:
                invoice.tax_amount = tax_amount
                invoice.totals.tax_amount = tax_amount
                
            if invoice.total_amount == 0:
                invoice.total_amount = total
                invoice.totals.total = total
                
            print(f"Recalculated totals: Subtotal={invoice.subtotal}, Tax={invoice.tax_amount}, Total={invoice.total_amount}")
    
    def _verify_with_ocr(self, invoice: Invoice) -> None:
        """Verify extracted data with OCR text if available."""
        if not self.ocr_text:
            return
            
        # Verify language
        language = self._verify_language(self.ocr_text)
        if language != 'en':
            print(f"Warning: Document language detected as {language}, not English")
            
        # Verify invoice number if not already extracted
        if not invoice.invoice_number:
            invoice_number_match = re.search(r"Invoice\s+Number\s+([\w-]+)", self.ocr_text, re.IGNORECASE)
            if invoice_number_match:
                invoice.invoice_number = invoice_number_match.group(1)
                print(f"Found invoice number from OCR: {invoice.invoice_number}")
            
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
