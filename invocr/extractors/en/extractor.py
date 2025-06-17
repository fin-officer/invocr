"""
English language extractor implementation.
"""
from typing import Any, Dict, List, Optional
import re
from datetime import datetime
import logging

from invocr.core.extractor import DataExtractor

class EnglishExtractor(DataExtractor):
    """English language extractor implementation."""

    def __init__(self, languages=None):
        super().__init__(languages)
        self.logger = logging.getLogger(__name__)

    def extract_invoice_data(self, text: str, document_type: str = "invoice") -> Dict[str, Any]:
        """Extract structured data from invoice text.
        
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
        
        # Extract totals
        totals = self._extract_totals(text, language)
        self.logger.debug(f"Extracted totals: {totals}")
        if totals:
            result["totals"] = totals
        
        # Extract payment info
        payment_info = self._extract_payment_info(text, language)
        self.logger.debug(f"Extracted payment info: {payment_info}")
        if payment_info:
            result["payment"] = payment_info
        
        # Validate and clean the extracted data
        self.logger.debug(f"Result before validation: {result}")
        self._validate_and_clean(result)
        self.logger.debug(f"Final result after validation: {result}")
        return result

    def _extract_basic_info(self, text: str, language: str) -> Dict[str, Any]:
        """Extract basic invoice information."""
        result = {}
        
        # Common date sub-patterns (no capturing group)
        date_subpatterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",  # DD/MM/YYYY or DD-MM-YYYY
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",    # YYYY-MM-DD or YYYY/MM/DD
            r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}",  # 01 Jan 2023
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,2}[,\s]+\d{4}"  # Jan 01, 2023
        ]
        date_union = "(?:" + "|".join(date_subpatterns) + ")"

        # Document number patterns
        doc_patterns = [
            r"(?:Invoice|Bill|Receipt|INV|FACTURE|FA)[\s:]*#?\s*([A-Z0-9-]{3,})",
            r"(?:No\.?|Number|Nr\.?|Ref\.?|Reference)[\s:]*#?\s*([A-Z0-9-]{3,})",
            r"(?:Document|Doc\.?)[\s:]*#?\s*([A-Z0-9-]{3,})"
        ]
        
        # PO number patterns
        po_patterns = [
            r"(?:PO|P\.O\.|Purchase Order)[\s:]*#?\s*([A-Z0-9-]+)",
            r"(?:Order|Reference)[\s:]*#?\s*([A-Z0-9-]+)"
        ]
        
        # Currency detection
        currency_patterns = [
            r"(?:Amount|Total|Balance|Subtotal|Amt\.?)[\s:]*([A-Z]{3}|[€$£¥])",
            r"([€$£¥])\s*\d+(?:\.\d{2})?"
        ]

        # Extract document number
        for pattern in doc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["document_number"] = match.group(1).strip()
                break
                
        # Extract PO number
        for pattern in po_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["po_number"] = match.group(1).strip()
                break

        # Extract issue date
        issue_date_patterns = [
            rf"(?:Date|Dated|Issued?|Invoice Date)[\s:]*({date_union})",
            rf"(?:Date)[\s:]*({date_union})"
        ]
        
        for pattern in issue_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                result["issue_date"] = self._parse_date(date_str)
                break

        # Extract due date
        due_date_patterns = [
            rf"(?:Due|Payment Due|Due Date|Payment Date)[\s:]*({date_union})",
            rf"(?:Payable by|Payment by)[\s:]*({date_union})"
        ]
        
        for pattern in due_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                result["due_date"] = self._parse_date(date_str)
                break
                
        # Detect currency
        for pattern in currency_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                currency = match.group(1)
                if currency in {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}:
                    result["currency"] = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}[currency]
                else:
                    result["currency"] = currency
                break
                
        return result
        
    def _parse_date(self, date_str: str) -> str:
        """Parse a date string into YYYY-MM-DD format."""
        from dateutil import parser
        try:
            date_obj = parser.parse(date_str, dayfirst=True, yearfirst=False)
            return date_obj.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            return date_str  # Return as-is if parsing fails

    def _extract_parties(self, text: str, language: str) -> Dict[str, Dict[str, str]]:
        """Extract seller and buyer information."""
        result = {
            "seller": {"name": "", "address": "", "tax_id": "", "email": "", "phone": ""},
            "buyer": {"name": "", "address": "", "tax_id": "", "email": "", "phone": ""}
        }
        
        # Common patterns for company information
        company_patterns = [
            r"(?i)(?:seller|vendor|provider|from)[\s:]*([\s\S]*?)(?=(?:buyer|client|customer|to)|$)",
            r"(?i)(?:bill to|invoice to|sold to)[\s:]*([\s\S]*?)(?=(?:ship to|$))"
        ]
        
        # Extract seller and buyer sections
        seller_text = ""
        buyer_text = ""
        
        for pattern in company_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for i, match in enumerate(matches):
                if i == 0:
                    seller_text += "\n" + match.group(1).strip()
                elif i == 1:
                    buyer_text += "\n" + match.group(1).strip()
        
        # Extract company names
        name_patterns = [
            r"^([^\n]{5,}?)\s*(?:\n|$)",
            r"(?:company|business|trading as|t/a|d/b/a|doing business as)[\s:]*([^\n]+)"
        ]
        
        # Extract seller info
        if seller_text:
            # Extract name
            for pattern in name_patterns:
                match = re.search(pattern, seller_text, re.IGNORECASE)
                if match:
                    result["seller"]["name"] = match.group(1).strip()
                    break
            
            # Extract tax ID (VAT, GST, etc.)
            tax_patterns = [
                r"(?:VAT|GST|TAX|Tax\s*ID|VAT\s*ID|VAT\s*No\.?|Tax\s*No\.?)[\s:]*([A-Z0-9\s-]+)",
                r"(?:Registration\s*No\.?|Reg\.?\s*No\.?|Reg\s*No\.?)[\s:]*([A-Z0-9\s-]+)"
            ]
            
            for pattern in tax_patterns:
                match = re.search(pattern, seller_text, re.IGNORECASE)
                if match:
                    result["seller"]["tax_id"] = match.group(1).strip()
                    break
            
            # Extract address
            address_match = re.search(r"(\d+[^\n]{10,}?)(?=\n\s*\n|\Z)", seller_text, re.DOTALL)
            if address_match:
                result["seller"]["address"] = "\n".join(
                    line.strip() for line in address_match.group(1).split("\n")
                    if line.strip()
                )
            
            # Extract contact info
            email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", seller_text)
            if email_match:
                result["seller"]["email"] = email_match.group(1)
                
            phone_match = re.search(r"(\+?[\d\s-]{8,})", seller_text)
            if phone_match:
                result["seller"]["phone"] = phone_match.group(1).strip()
        
        # Extract buyer info (similar to seller)
        if buyer_text:
            for pattern in name_patterns:
                match = re.search(pattern, buyer_text, re.IGNORECASE)
                if match:
                    result["buyer"]["name"] = match.group(1).strip()
                    break
            
            tax_patterns = [
                r"(?:VAT|GST|TAX|Tax\s*ID|VAT\s*ID|VAT\s*No\.?|Tax\s*No\.?)[\s:]*([A-Z0-9\s-]+)",
                r"(?:Registration\s*No\.?|Reg\.?\s*No\.?|Reg\s*No\.?)[\s:]*([A-Z0-9\s-]+)"
            ]
            
            for pattern in tax_patterns:
                match = re.search(pattern, buyer_text, re.IGNORECASE)
                if match:
                    result["buyer"]["tax_id"] = match.group(1).strip()
                    break
            
            address_match = re.search(r"(\d+[^\n]{10,}?)(?=\n\s*\n|\Z)", buyer_text, re.DOTALL)
            if address_match:
                result["buyer"]["address"] = "\n".join(
                    line.strip() for line in address_match.group(1).split("\n")
                    if line.strip()
                )
            
            email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", buyer_text)
            if email_match:
                result["buyer"]["email"] = email_match.group(1)
                
            phone_match = re.search(r"(\+?[\d\s-]{8,})", buyer_text)
            if phone_match:
                result["buyer"]["phone"] = phone_match.group(1).strip()
        
        return result

    def _extract_items(self, text: str, language: str) -> List[Dict[str, Any]]:
        """Extract line items from the document."""
        items = []
        
        # Common patterns for item tables
        item_patterns = [
            # Table with headers: Qty, Description, Unit Price, Amount
            r"(?:Qty|Quantity).*?(?:Description|Item).*?(?:Unit Price|Price).*?(?:Amount|Total)([\s\S]*?)(?=\n\s*\n|Subtotal|Total|$)",
            # Simple item lines: 1 x Product Name @ $10.00 = $10.00
            r"(\d+)\s*[x×]\s*([^@\n]+?)@\s*([$€£¥]?\s*\d+(?:\.\d{2})?)\s*[=]\s*([$€£¥]?\s*\d+(?:\.\d{2})?)",
            # Just item and price: Product Name $10.00
            r"(?m)^\s*([^\n]{5,}?)\s+([$€£¥]?\s*\d+(?:\.\d{2})?)\s*$"
        ]
        
        for pattern in item_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if len(match.groups()) >= 4:
                    # Table format
                    item = {
                        "quantity": match.group(1).strip(),
                        "description": match.group(2).strip(),
                        "unit_price": match.group(3).replace("$", "").replace(",", "").strip(),
                        "amount": match.group(4).replace("$", "").replace(",", "").strip()
                    }
                elif len(match.groups()) == 3:
                    # Simple item format
                    item = {
                        "description": match.group(1).strip(),
                        "unit_price": match.group(2).replace("$", "").replace(",", "").strip(),
                        "amount": match.group(2).replace("$", "").replace(",", "").strip()
                    }
                else:
                    continue
                
                # Clean up the values
                try:
                    item["quantity"] = float(item.get("quantity", 1))
                except (ValueError, TypeError):
                    item["quantity"] = 1.0
                    
                try:
                    item["unit_price"] = float(item.get("unit_price", 0))
                except (ValueError, TypeError):
                    item["unit_price"] = 0.0
                    
                try:
                    item["amount"] = float(item.get("amount", 0))
                except (ValueError, TypeError):
                    item["amount"] = 0.0
                
                items.append(item)
        
        return items

    def _extract_totals(self, text: str, language: str) -> Dict[str, float]:
        """Extract financial totals."""
        result = {"subtotal": 0.0, "tax_amount": 0.0, "total": 0.0, "tax_rate": 0.0}
        
        # Patterns for different total types
        patterns = [
            ("subtotal", r"(?:Subtotal|Sub-total|Total before tax)[\s:]*[$€£¥]?\s*(\d+(?:[.,]\d{2})?)"),
            ("tax_amount", r"(?:Tax|VAT|GST|Sales Tax)[\s:]*[$€£¥]?\s*(\d+(?:[.,]\d{2})?)"),
            ("tax_rate", r"(?:Tax|VAT|GST|Sales Tax)[\s:]*\(?(\d+(?:\.\d+)?)%\)?[\s:]*[$€£¥]?\s*(?:\d+(?:[.,]\d{2})?)?"),
            ("total", r"(?:Total|Amount Due|Balance Due|Grand Total)[\s:]*[$€£¥]?\s*(\d+(?:[.,]\d{2})?)")
        ]
        
        for field, pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(",", "."))
                    result[field] = value
                except (ValueError, IndexError):
                    continue
        
        # If we have items but no subtotal, calculate it
        if "subtotal" not in result or result["subtotal"] == 0.0:
            # Try to get subtotal from items
            items = self._extract_items(text, language)
            if items:
                subtotal = sum(item.get("amount", 0) for item in items)
                if subtotal > 0:
                    result["subtotal"] = subtotal
        
        # If we have subtotal and total but no tax, calculate it
        if result["subtotal"] > 0 and result["total"] > 0 and result["tax_amount"] == 0.0:
            tax_amount = result["total"] - result["subtotal"]
            if tax_amount > 0:
                result["tax_amount"] = tax_amount
                result["tax_rate"] = (tax_amount / result["subtotal"]) * 100
        
        return result

    def _extract_payment_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract payment method and bank account info."""
        result = {
            "payment_terms": "",
            "payment_method": "",
            "bank_name": "",
            "account_number": "",
            "routing_number": "",
            "swift_code": "",
            "iban": ""
        }
        
        # Payment terms
        terms_patterns = [
            r"(?:Payment Terms|Terms)[\s:]*([^\n]+)",
            r"(?:Net|Due)[\s:]*([^\n]+)"
        ]
        
        for pattern in terms_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["payment_terms"] = match.group(1).strip()
                break
        
        # Payment method
        payment_methods = [
            ("credit_card", r"(?:Visa|MasterCard|Amex|American Express|Discover|Credit Card|Debit Card)"),
            ("bank_transfer", r"(?:Bank Transfer|Wire Transfer|SEPA|ACH|IBAN|SWIFT)"),
            ("paypal", r"Pay(?:\s*|-)Pal"),
            ("check", r"Check|Cheque")
        ]
        
        for method, pattern in payment_methods:
            if re.search(pattern, text, re.IGNORECASE):
                result["payment_method"] = method
                break
        
        # Bank account details
        bank_patterns = [
            ("bank_name", r"Bank[\s:]*([^\n]+?)(?=\n|$)"),
            ("account_number", r"(?:Account|Acc\.?|A\/C)[\s:]*([A-Z0-9\s-]+)(?=\s|$)"),
            ("routing_number", r"(?:Routing|RTN|ABA|Routing No\.?)[\s:]*([0-9A-Z\s-]+)(?=\s|$)"),
            ("swift_code", r"(?:SWIFT|BIC|SWIFT Code|BIC Code)[\s:]*([A-Z0-9]{8,11})(?=\s|$)"),
            ("iban", r"(?:IBAN|International Bank Account Number)[\s:]*([A-Z]{2}[0-9A-Z\s-]{10,30})(?=\s|$)")
        ]
        
        for field, pattern in bank_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result[field] = match.group(1).strip()
        
        # Clean up empty values
        return {k: v for k, v in result.items() if v}

    def _detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        return "en"

    def extract_invoice_data(self, text: str, document_type: str = "invoice") -> dict:
        language = self._detect_language(text)
        data = {}
        data.update(self._extract_basic_info(text, language))
        parties = self._extract_parties(text, language)
        data["seller"] = parties.get("seller", {})
        data["buyer"] = parties.get("buyer", {})
        data["items"] = self._extract_items(text, language)
        data["totals"] = self._extract_totals(text, language)
        data.update(self._extract_payment_info(text, language))
        data["_metadata"] = {
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "document_type": document_type,
            "language": language,
        }
        return data

    def extract(self, text: str, language: str) -> Dict[str, Any]:
        """Extract all available information from the document."""
        result = self._extract_basic_info(text, language)
        result["parties"] = self._extract_parties(text, language)
        result["items"] = self._extract_items(text, language)
        result["totals"] = self._extract_totals(text, language)
        result["payment_info"] = self._extract_payment_info(text, language)
        return result
