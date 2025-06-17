"""
Spanish language extractor implementation.
"""
from typing import Any, Dict, List, Optional
import re
from datetime import datetime
import logging

from invocr.core.extractor import DataExtractor

class SpanishExtractor(DataExtractor):
    """Spanish language extractor implementation."""

    def __init__(self, languages=None):
        """Initialize the Spanish extractor with supported languages.

        Args:
            languages: List of language codes this extractor supports (default: ['es'])
        """
        super().__init__(languages or ["es"])
        self.logger = logging.getLogger(__name__)

    def extract_invoice_data(self, text: str, document_type: str = "invoice") -> Dict[str, Any]:
        """Extract structured data from Spanish invoice text.
        
        Args:
            text: Raw text from OCR
            document_type: Type of document (e.g., "factura", "recibo")
            
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
        
        # Document number (Número de factura)
        doc_number_match = re.search(
            r'(?i)(?:N[úu]mero|N[úu]m\.?|Factura)[\s:]*([A-Z0-9\-/]+)', 
            text
        )
        if doc_number_match:
            result["document_number"] = doc_number_match.group(1).strip()
        
        # Issue date (Fecha de emisión)
        issue_date_match = re.search(
            r'(?i)(?:Fecha de emisi[óo]n|Fecha)[\s:]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', 
            text
        )
        if issue_date_match:
            result["issue_date"] = self._parse_date(issue_date_match.group(1))
            
        # Due date (Fecha de vencimiento)
        due_date_match = re.search(
            r'(?i)(?:Fecha de vencimiento|Vencimiento|Pagar antes de)[\s:]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', 
            text
        )
        if due_date_match:
            result["due_date"] = self._parse_date(due_date_match.group(1))
            
        # Currency (Moneda)
        currency_match = re.search(
            r'(?i)(?:Moneda|Importe en)[\s:]*([A-Z]{3})', 
            text
        )
        if currency_match:
            result["currency"] = currency_match.group(1)
        else:
            # Default to EUR for Spanish invoices
            result["currency"] = "EUR"
            
        return result
        
    def _extract_parties(self, text: str, language: str) -> Dict[str, Any]:
        """Extract seller and buyer information."""
        result = {"seller": {}, "buyer": {}}
        
        # Extract seller name (Emisor/Vendedor)
        seller_name_match = re.search(
            r'(?i)(?:Emisor|Vendedor|Proveedor|Empresa)[\s:]*([^\n]+)(?:\n\s*[A-Z0-9\s,.-]+){2,}', 
            text
        )
        if seller_name_match:
            result["seller"]["name"] = seller_name_match.group(1).strip()
            
        # Extract seller tax ID (NIF/CIF)
        tax_id_match = re.search(
            r'(?i)(?:NIF|CIF|NIF\/CIF)[\s:]*([A-Z][0-9A-Z][0-9]{7}|[0-9]{8}[A-Z])', 
            text
        )
        if tax_id_match:
            result["seller"]["tax_id"] = tax_id_match.group(1).strip()
            
        # Extract buyer name (Receptor/Cliente)
        buyer_name_match = re.search(
            r'(?i)(?:Receptor|Cliente|Comprador)[\s:]*([^\n]+)(?:\n\s*[A-Z0-9\s,.-]+){2,}', 
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
        
        # Net amount (Base imponible)
        net_match = re.search(
            r'(?i)(?:Base imponible|Importe neto)[\s:]*([\d\s,.-]+)\s*[A-Z]{3}', 
            text
        )
        if net_match:
            result["net_amount"] = float(net_match.group(1).replace(" ", "").replace(".", "").replace(",", "."))
            
        # Tax amount (IVA/Impuestos)
        tax_match = re.search(
            r'(?i)(?:Total IVA|Importe del IVA|IVA\s*\d+%?)[\s:]*([\d\s,.-]+)\s*[A-Z]{3}', 
            text
        )
        if tax_match:
            result["tax_amount"] = float(tax_match.group(1).replace(" ", "").replace(".", "").replace(",", "."))
        
        # Tax rate (Tipo de IVA)
        tax_rate_match = re.search(
            r'(?i)(?:Tipo\s+)?(?:IVA|Tasa)[\s:]*(\d+)[\s%]*', 
            text
        )
        if tax_rate_match:
            result["tax_rate"] = float(tax_rate_match.group(1))
            
        # Total amount (Total factura)
        total_match = re.search(
            r'(?i)Total(?: factura| a pagar| general)[\s:]*([\d\s,.-]+)\s*([A-Z]{3})', 
            text
        )
        if total_match:
            result["total_amount"] = float(total_match.group(1).replace(" ", "").replace(".", "").replace(",", "."))
            if "currency" not in result:
                result["currency"] = total_match.group(2)
                
        return result
        
    def _extract_payment_info(self, text: str, language: str) -> Dict[str, Any]:
        """Extract payment information."""
        result = {}
        
        # Payment method (Forma de pago)
        payment_method_match = re.search(
            r'(?i)(?:Forma de pago|Método de pago|Pago)[\s:]*([^\n]+)', 
            text
        )
        if payment_method_match:
            result["payment_method"] = payment_method_match.group(1).strip()
            
        # Bank account (Cuenta bancaria)
        iban_match = re.search(
            r'(?i)(?:IBAN|Cuenta bancaria|N[úu]mero de cuenta)[\s:]*([A-Z]{2}\s*[0-9]{2}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{0,2})', 
            text
        )
        if iban_match:
            result["bank_account"] = iban_match.group(1).replace(" ", "")
            
        # BIC/SWIFT
        bic_match = re.search(
            r'(?i)(?:BIC|SWIFT|Código SWIFT)[\s:]*([A-Z0-9]{8,11})', 
            text
        )
        if bic_match:
            result["bic"] = bic_match.group(1)
            
        # Payment terms (Términos de pago)
        terms_match = re.search(
            r'(?i)(?:Términos de pago|Condiciones de pago|Pago a)[\s:]*([^\n]+)', 
            text
        )
        if terms_match:
            # Try to extract number of days
            days_match = re.search(r'(\d+)\s*(?:d[ií]as|d[ií]a)', terms_match.group(1), re.IGNORECASE)
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
            # Try different date formats (Spanish format first)
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
