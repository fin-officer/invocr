"""German language extractor implementation."""
import re
from typing import Dict, List, Any, Optional

from ..base import DataExtractor

class GermanExtractor(DataExtractor):
    """Extractor implementation for German language invoices."""
    
    def _load_extraction_patterns(self) -> Dict[str, Dict]:
        """Load extraction patterns for German language."""
        return {
            "de": {
                "document_number": [
                    r"(?:Rechnung|Rechnungsnummer|Nr\.?|Nummer)[\s:]+([A-Z0-9-]+)",
                    r"(?:Rechnung\s+[Nn]r\.?|Rechnungs-Nr\.?)[\s:]+([A-Z0-9-]+)"
                ],
                "date": [
                    r"(?:Rechnungsdatum|Datum|vom)[\s:]+([0-9]{1,2}[.-][0-9]{1,2}[.-][0-9]{2,4})",
                    r"(?:Rechnungsdatum|Datum|vom)[\s:]+(\d{1,2}\.\s+(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)[a-z]*\s+\d{4})",
                    r"(\d{1,2}\.\s+(?:Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)[a-z]*\.?\s+\d{4})"
                ],
                "due_date": [
                    r"(?:Zahlungsziel|Zahlbar bis|Fällig am|Fälligkeitsdatum)[\s:]+([0-9]{1,2}[.-][0-9]{1,2}[.-][0-9]{2,4})",
                    r"(?:Zahlungsziel|Zahlbar bis|Fällig am|Fälligkeitsdatum)[\s:]+(\d{1,2}\.\s+(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)[a-z]*\s+\d{4})",
                    r"(?:Zahlungsziel|Zahlbar bis|Fällig am|Fälligkeitsdatum)[\s:]+(\d{1,2}\.\s+(?:Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)[a-z]*\.?\s+\d{4})"
                ],
                "totals": {
                    "total": [
                        r"(?:Rechnungsbetrag|Gesamtbetrag|Endbetrag|Summe|Gesamtsumme)[\s:]+([0-9\s,]+[.,]\d{2})\s*(?:€|EUR|Euro)?",
                        r"(?i)gesamt[\s:]*([0-9\s,]+[.,]\d{2})\s*(?:€|EUR|Euro)?"
                    ],
                    "subtotal": [
                        r"(?:Nettobetrag|Netto|Zwischensumme)[\s:]+([0-9\s,]+[.,]\d{2})\s*(?:€|EUR|Euro)?",
                        r"(?i)netto[\s:]*([0-9\s,]+[.,]\d{2})\s*(?:€|EUR|Euro)?"
                    ],
                    "tax_amount": [
                        r"(?:MwSt\.?|Mehrwertsteuer|Umsatzsteuer)[\s:]+([0-9\s,]+[.,]\d{2})\s*(?:€|EUR|Euro)?",
                        r"(?i)mwst[\s:]*([0-9\s,]+[.,]\d{2})\s*(?:€|EUR|Euro)?"
                    ]
                },
                "items": {
                    "line_item": [
                        r"(\d+)\s+(.+?)\s+(\d+[.,]?\d*)\s+([0-9\s,]+[.,]\d{2})\s+([0-9\s,]+[.,]\d{2})\s*(?:€|EUR|Euro)?",
                        r"(.+?)\s+(\d+[.,]?\d*)\s+([0-9\s,]+[.,]\d{2})\s+([0-9\s,]+[.,]\d{2})\s*(?:€|EUR|Euro)?"
                    ]
                },
                "parties": {
                    "seller": [
                        r"(?:Rechnungssteller|Verkäufer|Lieferant|Absender)[\s:]+(.+?)(?=\s*(?:Rechnungsempfänger|Käufer|Kunde|$))",
                        r"(?:Firma|Name)[\s:]+(.+?)(?=\s*(?:USt-IdNr\.?|Steuernummer|$))"
                    ],
                    "buyer": [
                        r"(?:Rechnungsempfänger|Käufer|Kunde|Empfänger)[\s:]+(.+?)(?=\s*(?:Rechnungssteller|Verkäufer|$))",
                        r"(?:Kunden-Nr\.?|Kundennummer)[\s:]+(\d+)[\s\S]*?([^\n]+)(?=\s*(?:USt-IdNr\.?|Steuernummer|$))"
                    ]
                },
                "payment": {
                    "method": [
                        r"(?:Zahlungsart|Zahlungsweise|Zahlungsmethode)[\s:]+(.+?)(?=\s*(?:\n|$))",
                        r"(?:Überweisung|Banküberweisung|Kreditkarte|Lastschrift|PayPal|Barzahlung|Vorkasse)"
                    ],
                    "account": [
                        r"(?:Bankverbindung|Kontodaten|IBAN|Kontonummer)[\s:]+([A-Z]{2}[0-9]{2}[A-Z0-9]{1,30})(?=\s*(?:\n|$))",
                        r"(?:IBAN)[\s:]*([A-Z]{2}[0-9]{2}[A-Z0-9]{1,30})"
                    ]
                },
                "tax_id": {
                    "ustid": [
                        r"(?:USt-IdNr\.?|Umsatzsteuer-Identifikationsnummer)[\s:]*([A-Z]{2}[0-9]{9,10})",
                        r"(?:Steuernummer|Steuer-ID)[\s:]*([0-9]{10,11})"
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
                result["issue_date"] = self._parse_german_date(match.group(1))
                break
        
        # Extract due date
        for pattern in patterns["due_date"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result["due_date"] = self._parse_german_date(match.group(1))
                break
        
        return result
    
    def _extract_parties(self, text: str, language: str) -> Dict[str, Dict[str, str]]:
        """Extract seller and buyer information with tax IDs."""
        result = {"seller": {}, "buyer": {}}
        patterns = self.patterns[language]
        
        # Extract seller information
        for pattern in patterns["parties"]["seller"]:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                result["seller"]["name"] = match.group(1).strip()
                break
        
        # Extract buyer information
        for pattern in patterns["parties"]["buyer"]:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Handle patterns with multiple capture groups
                if len(match.groups()) > 1 and match.group(2):
                    result["buyer"]["customer_number"] = match.group(1).strip()
                    result["buyer"]["name"] = match.group(2).strip()
                else:
                    result["buyer"]["name"] = match.group(1).strip()
                break
        
        # Extract tax IDs (USt-IdNr. and Steuernummer)
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
        
        # Extract bank account (IBAN)
        for pattern in patterns["account"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                iban = match.group(1).replace(" ", "").upper()
                if self._validate_iban(iban):
                    result["bank_account"] = ' '.join(iban[i:i+4] for i in range(0, len(iban), 4))
                    break
        
        return result
    
    def _extract_tax_ids(self, text: str) -> Dict[str, str]:
        """Extract tax identification numbers (USt-IdNr. and Steuernummer)."""
        result = {}
        
        # Try to find USt-IdNr. near seller/buyer sections
        ustid_pattern = r'(?:USt-?ID[:\s]*|Umsatzsteuer-?Identifikationsnummer[:\s]*|MwSt-?Nr\.?[:\s]*)([A-Z]{2}[0-9]{9,10})'
        
        # Try to find Steuernummer
        steuernr_pattern = r'(?:Steuernummer|Steuer-?Nr\.?|St\.?-?Nr\.?)[\s:]*([0-9]{10,11})'
        
        # Search in seller section
        seller_section = re.search(r'(?i)(?:Rechnungssteller|Verkäufer|Lieferant|Absender).*?(?=Rechnungsempfänger|Käufer|Kunde|$)', 
                                 text, re.DOTALL)
        if seller_section:
            # Look for USt-IdNr.
            match = re.search(ustid_pattern, seller_section.group(0), re.IGNORECASE)
            if match:
                result["seller"] = match.group(1).replace(" ", "").replace("-", "")
            else:
                # Fall back to Steuernummer if USt-IdNr. not found
                match = re.search(steuernr_pattern, seller_section.group(0), re.IGNORECASE)
                if match:
                    result["seller"] = match.group(1).replace(" ", "").replace("-", "")
        
        # Search in buyer section
        buyer_section = re.search(r'(?i)(?:Rechnungsempfänger|Käufer|Kunde|Empfänger).*?(?=Rechnungssteller|Verkäufer|$)', 
                                text, re.DOTALL)
        if buyer_section:
            # Look for USt-IdNr.
            match = re.search(ustid_pattern, buyer_section.group(0), re.IGNORECASE)
            if match:
                result["buyer"] = match.group(1).replace(" ", "").replace("-", "")
            else:
                # Fall back to Steuernummer if USt-IdNr. not found
                match = re.search(steuernr_pattern, buyer_section.group(0), re.IGNORECASE)
                if match:
                    result["buyer"] = match.group(1).replace(" ", "").replace("-", "")
        
        return result
    
    @staticmethod
    def _parse_german_date(date_str: str) -> str:
        """Parse German date string into ISO format (YYYY-MM-DD)."""
        if not date_str or not isinstance(date_str, str):
            return ""
            
        date_str = date_str.strip()
        
        # German month names
        months = {
            'januar': '01', 'jan': '01', 'jan.': '01',
            'februar': '02', 'feb': '02', 'feb.': '02',
            'märz': '03', 'mär': '03', 'mrz': '03', 'mrz.': '03',
            'april': '04', 'apr': '04', 'apr.': '04',
            'mai': '05', 'may': '05',
            'juni': '06', 'jun': '06', 'jun.': '06',
            'juli': '07', 'jul': '07', 'jul.': '07',
            'august': '08', 'aug': '08', 'aug.': '08',
            'september': '09', 'sep': '09', 'sep.': '09', 'sept': '09', 'sept.': '09',
            'oktober': '10', 'okt': '10', 'okt.': '10', 'oct': '10', 'oct.': '10',
            'november': '11', 'nov': '11', 'nov.': '11',
            'dezember': '12', 'dez': '12', 'dez.': '12', 'dec': '12', 'dec.': '12'
        }
        
        # Try to parse date with month names
        for month_name, month_num in months.items():
            if month_name in date_str.lower():
                try:
                    # Handle formats like "15. Januar 2023"
                    parts = date_str.split()
                    day = parts[0].strip('.,')
                    year = parts[-1].strip('.,')
                    
                    # Ensure day and year are numeric
                    if not (day.isdigit() and year.isdigit()):
                        continue
                        
                    # Format as YYYY-MM-DD
                    return f"{year}-{month_num}-{day.zfill(2)}"
                except (IndexError, ValueError):
                    continue
        
        # Fall back to standard date parsing
        return DataExtractor._parse_date(date_str)
    
    @staticmethod
    def _validate_iban(iban: str) -> bool:
        """Validate IBAN format and checksum."""
        try:
            # Remove all non-alphanumeric characters and convert to uppercase
            iban = ''.join(c for c in iban.upper() if c.isalnum())
            
            # Check length (DE IBAN is 22 characters)
            if len(iban) != 22 or not iban.startswith('DE'):
                return False
            
            # Move first 4 characters to end
            iban_rearranged = iban[4:] + iban[:4]
            
            # Convert letters to numbers (A=10, B=11, ..., Z=35)
            iban_digits = []
            for char in iban_rearranged:
                if char.isdigit():
                    iban_digits.append(char)
                else:
                    iban_digits.append(str(10 + ord(char.upper()) - ord('A')))
            
            # Convert to integer and check mod 97
            iban_number = int(''.join(iban_digits))
            return iban_number % 97 == 1
            
        except (ValueError, IndexError):
            return False
