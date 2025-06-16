"""Polish language extractor implementation."""
import re
from typing import Dict, List, Any, Optional

from ..base import DataExtractor

class PolishExtractor(DataExtractor):
    """Extractor implementation for Polish language invoices."""
    
    def _load_extraction_patterns(self) -> Dict[str, Dict]:
        """Load extraction patterns for Polish language."""
        return {
            "pl": {
                "document_number": [
                    r"(?:Faktura|Faktura VAT|Numer faktury|Nr faktury)[\s:]+([A-Z0-9/-]+)",
                    r"(?:Nr\.?|Numer)[\s:]+([A-Z0-9/-]+)"
                ],
                "date": [
                    r"(?:Data wystawienia|Data)[\s:]+([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4})",
                    r"(\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)[a-z]*\s+\d{4})"
                ],
                "due_date": [
                    r"(?:Termin płatności|Do zapłaty do|Termin zapłaty)[\s:]+([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4})",
                    r"(?:Termin płatności|Do zapłaty do|Termin zapłaty)[\s:]+(\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)[a-z]*\s+\d{4})"
                ],
                "totals": {
                    "total": [
                        r"(?:Razem do zapłaty|Do zapłaty|Suma|Kwota całkowita)[\s:]+([0-9\s,]+[.,]\d{2})\s*(?:zł|PLN)?",
                        r"(?i)razem[\s:]*([0-9\s,]+[.,]\d{2})\s*(?:zł|PLN)?"
                    ],
                    "subtotal": [
                        r"(?:Wartość netto|Netto|Suma netto)[\s:]+([0-9\s,]+[.,]\d{2})\s*(?:zł|PLN)?",
                        r"(?i)netto[\s:]*([0-9\s,]+[.,]\d{2})\s*(?:zł|PLN)?"
                    ],
                    "tax_amount": [
                        r"(?:VAT|Podatek VAT|Kwota VAT)[\s:]+([0-9\s,]+[.,]\d{2})\s*(?:zł|PLN)?",
                        r"(?i)vat[\s:]*([0-9\s,]+[.,]\d{2})\s*(?:zł|PLN)?"
                    ]
                },
                "items": {
                    "line_item": [
                        r"(\d+)\s+(.+?)\s+(\d+[.,]?\d*)\s+([0-9\s,]+[.,]\d{2})\s+([0-9\s,]+[.,]\d{2})\s*(?:zł|PLN)?",
                        r"(.+?)\s+(\d+[.,]?\d*)\s+([0-9\s,]+[.,]\d{2})\s+([0-9\s,]+[.,]\d{2})\s*(?:zł|PLN)?"
                    ]
                },
                "parties": {
                    "seller": [
                        r"(?:Sprzedawca|Wystawca|Firma|Nazwa firmy)[\s:]+(.+?)(?=\s*(?:Nabywca|Kupujący|$))",
                        r"(?:Dane sprzedawcy|Dane wystawcy)[\s:]+(.+?)(?=\s*(?:Dane nabywcy|$))"
                    ],
                    "buyer": [
                        r"(?:Nabywca|Kupujący|Odbiorca)[\s:]+(.+?)(?=\s*(?:Sprzedawca|Wystawca|$))",
                        r"(?:Dane nabywcy|Dane odbiorcy)[\s:]+(.+?)(?=\s*(?:Dane sprzedawcy|$))"
                    ]
                },
                "payment": {
                    "method": [
                        r"(?:Forma płatności|Płatność|Sposób zapłaty)[\s:]+(.+?)(?=\s*(?:\n|$))",
                        r"(?:Przelew|Gotówka|Karta płatnicza|Przelewy24|BLIK|PayU)"
                    ],
                    "account": [
                        r"(?:Numer konta|Konto bankowe|Rachunek bankowy|IBAN)[\s:]+([A-Z0-9\s-]+" 
                        r"(?:\s*[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30})?)(?=\s*(?:\n|$))"
                    ]
                }
            }
        }
    
    def _extract_basic_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract basic document information."""
        result = {}
        patterns = self.patterns[language]
        
        # Extract document number
        for pattern in patterns["document_number"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result["document_number"] = match.group(1).strip()
                break
        
        # Extract issue date
        for pattern in patterns["date"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result["issue_date"] = self._parse_date(match.group(1))
                break
        
        # Extract due date
        for pattern in patterns["due_date"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result["due_date"] = self._parse_date(match.group(1))
                break
        
        return result
    
    def _extract_parties(self, text: str, language: str) -> Dict[str, Dict[str, str]]:
        """Extract seller and buyer information."""
        result = {"seller": {}, "buyer": {}}
        patterns = self.patterns[language]["parties"]
        
        # Extract seller information
        for pattern in patterns["seller"]:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                result["seller"]["name"] = match.group(1).strip()
                break
        
        # Extract buyer information
        for pattern in patterns["buyer"]:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                result["buyer"]["name"] = match.group(1).strip()
                break
        
        # Extract tax IDs
        tax_ids = self._extract_tax_ids(text)
        if tax_ids:
            if tax_ids.get("seller"):
                result["seller"]["tax_id"] = tax_ids["seller"]
            if tax_ids.get("buyer"):
                result["buyer"]["tax_id"] = tax_ids["buyer"]
        
        return result
    
    def _extract_items(self, text: str, language: str) -> List[Dict[str, Any]]:
        """Extract line items from text."""
        items = []
        patterns = self.patterns[language]["items"]["line_item"]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                item = self._parse_item_match(match, pattern)
                if item and item.get("description"):
                    items.append(item)
        
        return items
    
    def _parse_item_match(self, match: re.Match, pattern: str) -> Optional[Dict[str, Any]]:
        """Parse regex match into item dictionary."""
        groups = match.groups()
        
        if len(groups) >= 4:
            try:
                return {
                    "description": groups[0].strip() if groups[0] else "",
                    "quantity": float(groups[1].replace(",", ".")) if groups[1] else 1,
                    "unit_price": float(groups[2].replace(" ", "").replace(",", ".")) if groups[2] else 0,
                    "total_price": float(groups[3].replace(" ", "").replace(",", ".")) if groups[3] else 0,
                }
            except (ValueError, IndexError):
                return None
        return None
    
    def _extract_totals(self, text: str, language: str) -> Dict[str, float]:
        """Extract financial totals."""
        totals = {"subtotal": 0.0, "tax_amount": 0.0, "total": 0.0}
        patterns = self.patterns[language]["totals"]
        
        for total_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    try:
                        value_str = match.group(1).replace(" ", "").replace(",", ".")
                        value = float(re.sub(r"[^\d.]", "", value_str))
                        totals[total_type] = value
                        break
                    except (ValueError, IndexError):
                        continue
        
        return totals
    
    def _extract_payment_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract payment method and bank account info."""
        result = {}
        patterns = self.patterns[language]["payment"]
        
        # Extract payment method
        for pattern in patterns["method"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result["payment_method"] = match.group(1).strip() if match.lastindex else match.group(0).strip()
                break
        
        # Extract bank account
        for pattern in patterns["account"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result["bank_account"] = match.group(1).strip()
                break
        
        return result
    
    def _extract_tax_ids(self, text: str) -> Dict[str, str]:
        """Extract tax identification numbers (NIP) for seller and buyer."""
        result = {}
        
        # NIP format: 10 digits, optionally separated by hyphens or spaces
        nip_pattern = r'(?:NIP|VAT)[\s:]*([0-9]{3}[- ]?[0-9]{2,3}[- ]?[0-9]{2}[- ]?[0-9]{2}[- ]?[0-9]{2})'
        
        # Try to find NIPs near seller/buyer sections
        seller_match = re.search(
            r'(?:Sprzedawca|Wystawca).*?' + nip_pattern,
            text, re.IGNORECASE | re.DOTALL
        )
        
        if seller_match and seller_match.group(1):
            result["seller"] = seller_match.group(1).replace(" ", "").replace("-", "")
        
        buyer_match = re.search(
            r'(?:Nabywca|Kupujący|Odbiorca).*?' + nip_pattern,
            text, re.IGNORECASE | re.DOTALL
        )
        
        if buyer_match and buyer_match.group(1):
            result["buyer"] = buyer_match.group(1).replace(" ", "").replace("-", "")
        
        return result
