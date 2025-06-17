"""
German language extractor implementation.
"""
from typing import Any, Dict, List, Optional
import re
from datetime import datetime
import logging

from invocr.core.extractor import DataExtractor

class GermanExtractor(DataExtractor):
    """German language extractor implementation."""

    def __init__(self, languages=None):
        """Initialize the German extractor with supported languages.

        Args:
            languages: List of language codes this extractor supports (default: ['de'])
        """
        super().__init__(languages or ["de"])
        self.logger = logging.getLogger(__name__)

    def extract_invoice_data(self, text: str, document_type: str = "invoice") -> Dict[str, Any]:
        """Extract structured data from German invoice text.
        
        Args:
            text: Raw text from OCR
            document_type: Type of document (e.g., "invoice", "receipt")
            
        Returns:
            Dict containing structured invoice data
        """
        self.logger.debug(f"Extracting invoice data. Document type: {document_type}")
        self.logger.debug(f"Raw text input (first 500 chars): {text[:500]}")
        result = self._get_document_template(document_type)
        
        # Detect language if not specified
        language = self._detect_language(text)
        self.logger.debug(f"Detected language: {language}")
        
        # Extract basic info
        basic_info = self._extract_basic_info(text, language)
        self.logger.debug(f"Extracted basic info: {basic_info}")
        result.update(basic_info)
        
        # Extract parties (seller/buyer)
        parties = self._extract_parties(text, language)
        self.logger.debug(f"Extracted parties: {parties}")
        result.update(parties)
        
        # Extract line items
        items = self._extract_items(text, language)
        self.logger.debug(f"Extracted items: {items}")
        if items:
            result["items"] = items
            
        # Extract totals and payment info
        totals = self._extract_totals(text, language)
        self.logger.debug(f"Extracted totals: {totals}")
        result.update(totals)
        
        payment_info = self._extract_payment_info(text, language)
        self.logger.debug(f"Extracted payment info: {payment_info}")
        result.update(payment_info)
        
        # Validate and clean the result
        self._validate_and_clean(result)
        
        return result
        
    def _extract_basic_info(self, text: str, language: str) -> Dict[str, Any]:
        """Extract basic invoice information."""
        result = {}
        
        # Document number (Rechnungsnummer)
        doc_number_match = re.search(
            r'(?i)(?:Rechnungsnummer|Rechnungs-Nr\.?|Nr\.?)[:\s]*(\w[\w\s-]*\d+)', 
            text
        )
        if doc_number_match:
            result["document_number"] = doc_number_match.group(1).strip()
        
        # Issue date (Rechnungsdatum)
        issue_date_match = re.search(
            r'(?i)(?:Rechnungsdatum|Datum)[:\s]*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})', 
            text
        )
        if issue_date_match:
            result["issue_date"] = self._parse_date(issue_date_match.group(1))
            
        # Due date (Fälligkeitsdatum)
        due_date_match = re.search(
            r'(?i)(?:Fällig(?:keit)?(?:sd?atum)?|Zahlbar bis)[:\s]*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})', 
            text
        )
        if due_date_match:
            result["due_date"] = self._parse_date(due_date_match.group(1))
            
        # Currency (Währung)
        currency_match = re.search(
            r'(?i)(?:Währung|Betrag in)[:\s]*([A-Z]{3})', 
            text
        )
        if currency_match:
            result["currency"] = currency_match.group(1)
        else:
            # Default to EUR for German invoices
            result["currency"] = "EUR"
            
        return result
        
    def _extract_parties(self, text: str, language: str) -> Dict[str, Any]:
        """Extract seller and buyer information."""
        result = {"seller": {}, "buyer": {}}
        
        # Extract seller name (Verkäufer/Lieferant)
        seller_name_match = re.search(
            r'(?i)(?:Verkäufer|Lieferant|Rechnungssteller)[:\s]*([^\n]+)(?:\n\s*[A-Z0-9\s,.-]+){2,}', 
            text
        )
        if seller_name_match:
            result["seller"]["name"] = seller_name_match.group(1).strip()
            
        # Extract seller tax ID (USt-IdNr.)
        tax_id_match = re.search(
            r'(?i)(?:USt-?ID|Umsatzsteuer-?Identifikationsnummer)[:\s]*([A-Z]{2}\s*[0-9]+[0-9A-Z]*)', 
            text
        )
        if tax_id_match:
            result["seller"]["tax_id"] = tax_id_match.group(1).strip()
            
        # Extract buyer name (Käufer/Rechnungsempfänger)
        buyer_name_match = re.search(
            r'(?i)(?:Käufer|Rechnungsempfänger)[:\s]*([^\n]+)(?:\n\s*[A-Z0-9\s,.-]+){2,}', 
            text
        )
        if buyer_name_match:
            result["buyer"]["name"] = buyer_name_match.group(1).strip()
            
        return result
        
    def _extract_items(self, text: str, language: str) -> List[Dict[str, Any]]:
        """Extract line items from the invoice."""
        items = []
        
        # Look for item patterns in the text
        item_matches = re.finditer(
            r'(?i)(\d+[\.,]?\d*)\s+(?:x|X|\*)\s+([^\n]+?)\s+(\d+[\s,.]\d{2})\s+[A-Z]{3}\s+(\d+[\s,.]\d{2})',
            text
        )
        
        for match in item_matches:
            items.append({
                "description": match.group(2).strip(),
                "quantity": float(match.group(1).replace(",", ".")),
                "unit_price": float(match.group(3).replace(",", ".").replace(" ", "")),
                "amount": float(match.group(4).replace(",", ".").replace(" ", "")),
            })
            
        return items
        
    def _extract_totals(self, text: str, language: str) -> Dict[str, Any]:
        """Extract total amounts from the invoice."""
        result = {}
        
        # Net amount (Nettobetrag)
        net_match = re.search(
            r'(?i)(?:Nettobetrag|Netto(?:summe)?|Zwischensumme)[:\s]*([\d\s,.-]+)\s*[A-Z]{3}', 
            text
        )
        if net_match:
            result["net_amount"] = float(net_match.group(1).replace(" ", "").replace(",", "."))
            
        # Tax amount (Mehrwertsteuer/Umsatzsteuer)
        tax_match = re.search(
            r'(?i)(?:Mehrwertsteuer|Umsatzsteuer|USt\.?|MwSt\.?)[\s\d%]*(?:\d+[\s,.]\d+)\s*[A-Z]{3}\s*([\d\s,.-]+)\s*[A-Z]{3}', 
            text
        )
        if tax_match:
            result["tax_amount"] = float(tax_match.group(1).replace(" ", "").replace(",", "."))
        
        # Tax rate (Steuersatz)
        tax_rate_match = re.search(
            r'(?i)(?:Mehrwertsteuer|Umsatzsteuer|USt\.?|MwSt\.?)[\s]*(\d+)[\s%]*', 
            text
        )
        if tax_rate_match:
            result["tax_rate"] = float(tax_rate_match.group(1))
            
        # Total amount (Gesamtbetrag)
        total_match = re.search(
            r'(?i)(?:Gesamtbetrag|Endbetrag|Rechnungsbetrag|Zu zahlender Betrag)[:\s]*([\d\s,.-]+)\s*([A-Z]{3})', 
            text
        )
        if total_match:
            result["total_amount"] = float(total_match.group(1).replace(" ", "").replace(",", "."))
            if "currency" not in result:
                result["currency"] = total_match.group(2)
                
        return result
        
    def _extract_payment_info(self, text: str, language: str) -> Dict[str, Any]:
        """Extract payment information."""
        result = {}
        
        # Payment method (Zahlungsart)
        payment_method_match = re.search(
            r'(?i)(?:Zahlungsart|Zahlungsweise|Bezahlung)[:\s]*([^\n]+)', 
            text
        )
        if payment_method_match:
            result["payment_method"] = payment_method_match.group(1).strip()
            
        # Bank account (Bankverbindung)
        iban_match = re.search(
            r'(?i)(?:IBAN|Kontonummer|Konto-Nr\.?)[:\s]*([A-Z]{2}\s*[0-9]{2}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{0,2})', 
            text
        )
        if iban_match:
            result["bank_account"] = iban_match.group(1).replace(" ", "")
            
        # BIC/SWIFT
        bic_match = re.search(
            r'(?i)(?:BIC|SWIFT|Bankleitzahl)[:\s]*([A-Z0-9]{8,11})', 
            text
        )
        if bic_match:
            result["bic"] = bic_match.group(1)
            
        # Payment terms (Zahlungsbedingungen)
        terms_match = re.search(
            r'(?i)(?:Zahlungsbedingungen|Zahlbar innerhalb von|Zahlungsziel)[\s:]*([^\n]+)', 
            text
        )
        if terms_match:
            # Try to extract number of days
            days_match = re.search(r'(\d+)\s*(?:Tage|Tagen|Tag)', terms_match.group(1))
            if days_match:
                result["payment_terms_days"] = int(days_match.group(1))
            else:
                result["payment_terms"] = terms_match.group(1).strip()
            
        return result
        
    def _parse_date(self, date_str: str) -> str:
        """Parse date string into YYYY-MM-DD format."""
        try:
            # Handle different date separators
            date_str = date_str.replace(".", "-").replace("/", "-")
            # Try different date formats (German format first)
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d-%m-%y"):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return date_str
        except Exception as e:
            self.logger.warning(f"Failed to parse date '{date_str}': {e}")
            return date_str
        
    def _validate_and_clean(self, data: Dict[str, Any]) -> None:
        """Validate and clean extracted data."""
        # Ensure required fields are present
        if "document_number" not in data:
            self.logger.warning("Document number not found")
            
        if "issue_date" not in data:
            self.logger.warning("Issue date not found")
            
        if "total_amount" not in data:
            self.logger.warning("Total amount not found")
