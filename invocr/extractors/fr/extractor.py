"""
French language extractor implementation.
"""
from typing import Any, Dict, List, Optional
import re
from datetime import datetime
import logging

from invocr.core.extractor import DataExtractor

class FrenchExtractor(DataExtractor):
    """French language extractor implementation."""

    def __init__(self, languages=None):
        """Initialize the French extractor with supported languages.

        Args:
            languages: List of language codes this extractor supports (default: ['fr'])
        """
        super().__init__(languages or ["fr"])
        self.logger = logging.getLogger(__name__)

    def extract_invoice_data(self, text: str, document_type: str = "invoice") -> Dict[str, Any]:
        """Extract structured data from French invoice text.
        
        Args:
            text: Raw text from OCR
            document_type: Type of document (e.g., "facture", "reçu")
            
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
        
        # Document number (Numéro de facture)
        doc_number_match = re.search(
            r'(?i)(?:N[°º]|Num[ée]ro|Facture|Ref)[\s:]*([A-Z0-9\-/]+)', 
            text
        )
        if doc_number_match:
            result["document_number"] = doc_number_match.group(1).strip()
        
        # Issue date (Date de facturation)
        issue_date_match = re.search(
            r'(?i)(?:Date de facturation|Date d''émission|Date)[\s:]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', 
            text
        )
        if issue_date_match:
            result["issue_date"] = self._parse_date(issue_date_match.group(1))
            
        # Due date (Date d'échéance)
        due_date_match = re.search(
            r'(?i)(?:Date d''[ée]ch[ée]ance|Date de paiement|[ée]ch[ée]ance)[\s:]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', 
            text
        )
        if due_date_match:
            result["due_date"] = self._parse_date(due_date_match.group(1))
            
        # Currency (Devise)
        currency_match = re.search(
            r'(?i)(?:Devise|Montant en)[\s:]*([A-Z]{3})', 
            text
        )
        if currency_match:
            result["currency"] = currency_match.group(1)
        else:
            # Default to EUR for French invoices
            result["currency"] = "EUR"
            
        return result
        
    def _extract_parties(self, text: str, language: str) -> Dict[str, Any]:
        """Extract seller and buyer information."""
        result = {"seller": {}, "buyer": {}}
        
        # Extract seller name (Vendeur/Fournisseur)
        seller_name_match = re.search(
            r'(?i)(?:Vendeur|Fournisseur|Soci[ée]t[ée]|Entreprise)[\s:]*([^\n]+)(?:\n\s*[A-Z0-9\s,.-]+){2,}', 
            text
        )
        if seller_name_match:
            result["seller"]["name"] = seller_name_match.group(1).strip()
            
        # Extract seller tax ID (SIRET/SIREN/TVA)
        siret_match = re.search(
            r'(?i)(?:SIRET|SIREN|TVA|N° SIRET)[\s:]*([0-9\s]{14}|[0-9\s]{9})', 
            text
        )
        if siret_match:
            result["seller"]["tax_id"] = siret_match.group(1).replace(" ", "")
            
        # Extract buyer name (Acheteur/Client)
        buyer_name_match = re.search(
            r'(?i)(?:Acheteur|Client|Destinataire)[\s:]*([^\n]+)(?:\n\s*[A-Z0-9\s,.-]+){2,}', 
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
            r'(?i)(\d+[\.,]?\d*)\s+x\s+([^\n]+?)\s+(\d+[\s,.]\d{2})\s+[A-Z]{3}\s+(\d+[\s,.]\d{2})',
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
        
        # Net amount (Montant HT)
        net_match = re.search(
            r'(?i)(?:Montant HT|Total HT|Net [àa] payer)[\s:]*([\d\s,.-]+)\s*[A-Z]{3}', 
            text
        )
        if net_match:
            result["net_amount"] = float(net_match.group(1).replace(" ", "").replace(",", "."))
            
        # Tax amount (TVA/Montant TVA)
        tax_match = re.search(
            r'(?i)(?:TVA|Montant TVA|Total TVA)[\s:]*([\d\s,.-]+)\s*[A-Z]{3}', 
            text
        )
        if tax_match:
            result["tax_amount"] = float(tax_match.group(1).replace(" ", "").replace(",", "."))
        
        # Tax rate (Taux de TVA)
        tax_rate_match = re.search(
            r'(?i)(?:Taux\s+)?(?:TVA|TVA\s*\d+%?)[\s:]*(\d+)[\s%]*', 
            text
        )
        if tax_rate_match:
            result["tax_rate"] = float(tax_rate_match.group(1))
            
        # Total amount (Total TTC)
        total_match = re.search(
            r'(?i)Total(?:\s+TTC|\s+[àa]\s+payer|\s+g[ée]n[ée]ral)?[\s:]*([\d\s,.-]+)\s*([A-Z]{3})', 
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
        
        # Payment method (Mode de paiement)
        payment_method_match = re.search(
            r'(?i)(?:Mode de paiement|Moyen de paiement|Paiement)[\s:]*([^\n]+)', 
            text
        )
        if payment_method_match:
            result["payment_method"] = payment_method_match.group(1).strip()
            
        # Bank account (Coordonnées bancaires)
        iban_match = re.search(
            r'(?i)(?:IBAN|R[ée]f[ée]rence bancaire|Compte bancaire)[\s:]*([A-Z]{2}\s*[0-9]{2}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{0,2})', 
            text
        )
        if iban_match:
            result["bank_account"] = iban_match.group(1).replace(" ", "")
            
        # BIC/SWIFT
        bic_match = re.search(
            r'(?i)(?:BIC|SWIFT|Code banque)[\s:]*([A-Z0-9]{8,11})', 
            text
        )
        if bic_match:
            result["bic"] = bic_match.group(1)
            
        # Payment terms (Conditions de paiement)
        terms_match = re.search(
            r'(?i)(?:Conditions de paiement|Modalit[ée]s de paiement|Paiement sous)[\s:]*([^\n]+)', 
            text
        )
        if terms_match:
            # Try to extract number of days
            days_match = re.search(r'(\d+)\s*(?:jours|jour)', terms_match.group(1), re.IGNORECASE)
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
            # Try different date formats (French format first)
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
