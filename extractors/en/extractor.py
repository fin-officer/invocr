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
                    r"Invoice\s+Number\s+([0-9]+)",
                    r"(?:Invoice|Bill|Receipt)\s*[#:]?\s*([A-Z0-9-]+)",
                    r"(?:No\.?|Number|Nr\.?)\s*[:#]?\s*([A-Z0-9-]+)"
                ],
                "date": [
                    r"(?:Date|Dated|Issued?)\s*[:]?\s*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})",
                    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
                    r"Invoice\s+Date\s+(\d{1,2}-[A-Z]{3}-\d{4})"
                ],
                "due_date": [
                    r"(?:Due\s*Date|Payment\s*Due|Due)\s*[:]?\s*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})",
                    r"(?:Due\s*Date|Payment\s*Due|Due)\s*[:]?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
                ],
                "totals": {
                    "total": [
                        r"(?:Total|Amount Due|Balance Due|Grand Total)\s*[:]?\s*([0-9,.]+)",
                        r"(?i)(?:total|amount)[\s:]*\$?\s*([\d,.]+)",
                        r"GRAND TOUAL\s*\(?[A-Z]{3}\)?\s*([\d,.]+)",
                        r"TOTAL\s+([\d,.]+)",
                        r"Invoice Total[\s\S]+?GRAND TOUAL\s*\(?[A-Z]{3}\)?\s*P?([\d,.]+)"
                    ],
                    "subtotal": [
                        r"(?:Sub-?total|Net Amount)\s*[:]?\s*([0-9,.]+)",
                        r"(?i)sub-?total[\s:]*\$?\s*([\d,.]+)",
                        r"NET AMOUNT\s*\(?[A-Z]{3}\)?\s*([\d,.]+)"
                    ],
                    "tax_amount": [
                        r"(?:VAT|TAX|GST|Sales Tax)\s*[:]?\s*([0-9,.]+)",
                        r"(?i)(?:vat|tax|gst)[\s:]*\$?\s*([\d,.]+)",
                        r"TAXES\s*\(?[A-Z]{3}\)?\s*([\d,.]+)"
                    ]
                },
                "items": {
                    "line_item": [
                        r"(\d+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+([0-9,.]+)\s+([0-9,.]+)",
                        r"(.+?)\s+(\d+(?:\.\d+)?)\s+([0-9,.]+)\s+([0-9,.]+)",
                        r"(\d+)\s+([A-Za-z]+)\s+(\d+(?:\.\d+)?)\s+([A-Z]{2})\s+([0-9,.]+)\s+([0-9,.]+)",
                        r"(\d+)\s+([\w\s]+)\s+(\d+)\s+([A-Z]{2})\s+([\d,.]+)\s+([\d,.]+)\s+[\d.%]+\s+[\d.]+\s+([\d,.]+)"
                    ]
                },
                "parties": {
                    "seller": [
                        r"(?:From|Seller|Vendor|Provider)[\s:]+(.+?)(?=\s*(?:To|Buyer|Client|Customer|$))",
                        r"(?:Bill From|Issuer)[\s:]+(.+?)(?=\s*(?:Bill To|Recipient|$))",
                        r"(Adobe Systems Software Ireland Ltd[\s\S]+?)(?=Bill To|Customer Number)",
                        r"([\w\s]+Ltd)\s+ORIGINAL[\s\S]+?(?=Bill To|Customer Number)"
                    ],
                    "buyer": [
                        r"(?:To|Bill To|Buyer|Client|Customer)[\s:]+(.+?)(?=\s*(?:From|Seller|Vendor|$))",
                        r"(?:Ship To|Recipient)[\s:]+(.+?)(?=\s*(?:From|Issuer|$))",
                        r"Bill To\s+([\s\S]+?)(?=Service Term:|PRODUCT NUMBER|Customer VAT No:)",
                        r"Bill To\s+([\w\s\d\.-]+)\s+\d{5}\s+[\w\s]+"
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
        """Extract line items from the document."""
        items = []
        patterns = self.patterns[language]["items"]["line_item"]
        
        # Special case for Adobe invoices
        adobe_pattern = r"PRODUCT\s+NUMBER\s+PRODUCT\s+DESCRIPTION\s+QUANTITY\s+UNIT\s+UNIT\s+PRICE\s+NET\s+AMOUNT[\s\S]+?([0-9]+)\s+([\w\s]+)\s+([0-9]+)\s+([A-Z]{2})\s+([0-9,.]+)\s+([0-9,.]+)"
        adobe_match = re.search(adobe_pattern, text, re.IGNORECASE)
        if adobe_match:
            product_number = adobe_match.group(1).strip()
            description = adobe_match.group(2).strip()
            quantity = self._parse_float(adobe_match.group(3))
            unit = adobe_match.group(4).strip()
            unit_price = self._parse_float(adobe_match.group(5))
            total_price = self._parse_float(adobe_match.group(6))
            
            items.append({
                "description": f"{description} (Product #{product_number})",
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "total_price": total_price
            })
            return items
        
        # Standard patterns
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 3:
                    # Handle different pattern formats
                    if len(groups) == 3:  # description, quantity, price
                        description = groups[0].strip()
                        quantity = self._parse_float(groups[1])
                        unit_price = self._parse_float(groups[2])
                        total_price = 0.0
                    elif len(groups) == 4:  # description, quantity, unit_price, total_price
                        description = groups[0].strip()
                        quantity = self._parse_float(groups[1])
                        unit_price = self._parse_float(groups[2])
                        total_price = self._parse_float(groups[3])
                    elif len(groups) == 5:  # id, description, quantity, unit_price, total_price
                        description = groups[1].strip()
                        quantity = self._parse_float(groups[2])
                        unit_price = self._parse_float(groups[3])
                        total_price = self._parse_float(groups[4])
                    elif len(groups) == 6:  # id, description, quantity, unit, unit_price, total_price
                        description = groups[1].strip()
                        quantity = self._parse_float(groups[2])
                        unit_price = self._parse_float(groups[4])
                        total_price = self._parse_float(groups[5])
                    elif len(groups) == 7:  # id, description, quantity, unit, unit_price, net_amount, total
                        description = groups[1].strip()
                        quantity = self._parse_float(groups[2])
                        unit_price = self._parse_float(groups[4])
                        net_amount = self._parse_float(groups[5])
                        total_price = self._parse_float(groups[6])
                    else:  # Handle any other format with at least 3 groups
                        description = groups[0].strip()
                        quantity = self._parse_float(groups[1])
                        unit_price = self._parse_float(groups[2])
                        total_price = 0.0
                        
                    items.append({
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total_price": total_price
                    })
        
        return items
    
    def _parse_float(self, value_str: str) -> float:
        """Parse string into float, handling various formats."""
        if not value_str:
            return 0.0
            
        # Remove any non-numeric characters except for decimal point
        clean_str = re.sub(r"[^\d.]", "", str(value_str).replace(",", "."))
        
        try:
            # Handle multiple decimal points by keeping only the first one
            parts = clean_str.split('.')
            if len(parts) > 2:
                clean_str = parts[0] + '.' + ''.join(parts[1:])
            return float(clean_str) if clean_str else 0.0
        except (ValueError, TypeError):
            return 0.0
    
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
        
        # Special case for Adobe invoices
        adobe_pattern = r"Invoice Total\s+NET AMOUNT\s*\([A-Z]{3}\)\s*([\d,.]+)\s+TAXES[^\n]+\s+([\d,.]+)\s+.*?GRAND TOUAL\s*\([A-Z]{3}\)\s*P?([\d,.]+)"
        adobe_match = re.search(adobe_pattern, text, re.IGNORECASE | re.MULTILINE)
        if adobe_match:
            try:
                subtotal = self._parse_float(adobe_match.group(1))
                tax = self._parse_float(adobe_match.group(2))
                total = self._parse_float(adobe_match.group(3))
                
                totals["subtotal"] = subtotal
                totals["tax_amount"] = tax
                totals["total"] = total
                return totals
            except (ValueError, IndexError):
                pass  # Fall back to standard extraction
        
        # Standard extraction
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
