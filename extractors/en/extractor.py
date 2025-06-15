"""English language extractor implementation."""
import re
from typing import Dict, List, Any, Optional

from ..base import DataExtractor

class EnglishExtractor(DataExtractor):
    """Extractor implementation for English language invoices."""
    
    def _load_extraction_patterns(self) -> Dict[str, Dict]:
        """Load extraction patterns for English language."""
        return {
            "en": {
                "document_number": [
                    r"(?:Invoice|Bill|Receipt)\s*[#:]?\s*([A-Z0-9-]+)",
                    r"(?:No\.?|Number|Nr\.?)\s*[:#]?\s*([A-Z0-9-]+)"
                ],
                "date": [
                    r"(?:Date|Dated|Issued?)\s*[:]?\s*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})",
                    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
                ],
                "due_date": [
                    r"(?:Due\s*Date|Payment\s*Due|Due)\s*[:]?\s*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})",
                    r"(?:Due\s*Date|Payment\s*Due|Due)\s*[:]?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
                ],
                "totals": {
                    "total": [
                        r"(?:Total|Amount Due|Balance Due|Grand Total)\s*[:]?\s*([0-9,.]+)",
                        r"(?i)(?:total|amount)[\s:]*\$?\s*([\d,.]+)"
                    ],
                    "subtotal": [
                        r"(?:Sub-?total|Net Amount)\s*[:]?\s*([0-9,.]+)",
                        r"(?i)sub-?total[\s:]*\$?\s*([\d,.]+)"
                    ],
                    "tax_amount": [
                        r"(?:VAT|TAX|GST|Sales Tax)\s*[:]?\s*([0-9,.]+)",
                        r"(?i)(?:vat|tax|gst)[\s:]*\$?\s*([\d,.]+)"
                    ]
                },
                "items": {
                    "line_item": [
                        r"(\d+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+([0-9,.]+)\s+([0-9,.]+)",
                        r"(.+?)\s+(\d+(?:\.\d+)?)\s+([0-9,.]+)\s+([0-9,.]+)"
                    ]
                },
                "parties": {
                    "seller": [
                        r"(?:From|Seller|Vendor|Provider)[\s:]+(.+?)(?=\s*(?:To|Buyer|Client|Customer|$))",
                        r"(?:Bill From|Issuer)[\s:]+(.+?)(?=\s*(?:Bill To|Recipient|$))"
                    ],
                    "buyer": [
                        r"(?:To|Bill To|Buyer|Client|Customer)[\s:]+(.+?)(?=\s*(?:From|Seller|Vendor|$))",
                        r"(?:Ship To|Recipient)[\s:]+(.+?)(?=\s*(?:From|Issuer|$))"
                    ]
                },
                "payment": {
                    "method": [
                        r"(?:Payment Method|Paid by|Payment by)[\s:]+(.+?)(?=\s*(?:\n|$))",
                        r"(?:Credit Card|Bank Transfer|Cash|Check|PayPal|Stripe)"
                    ],
                    "account": [
                        r"(?:Account|IBAN|Bank Account|Account Number)[\s:]+([A-Z0-9\s-]+" 
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
                    "quantity": float(groups[1].replace(",", "")) if groups[1] else 1,
                    "unit_price": float(groups[2].replace(",", "")) if groups[2] else 0,
                    "total_price": float(groups[3].replace(",", "")) if groups[3] else 0,
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
                        value_str = match.group(1).replace(" ", "").replace(",", "")
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
