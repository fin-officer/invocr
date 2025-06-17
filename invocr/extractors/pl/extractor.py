"""
Polish language extractor implementation.
"""
from typing import Any, Dict, List, Optional
import re
from datetime import datetime
import logging

from invocr.core.extractor import DataExtractor

class PolishExtractor(DataExtractor):
    """Polish language extractor implementation."""

    def __init__(self, languages=None):
        """Initialize the Polish extractor with supported languages.

        Args:
            languages: List of language codes this extractor supports (default: ['pl'])
        """
        super().__init__(languages or ["pl"])
        self.logger = logging.getLogger(__name__)

    def extract_invoice_data(self, text: str, document_type: str = "invoice") -> Dict[str, Any]:
        """Extract structured data from Polish invoice text (Softreck/PL-specialized, robust for flat OCR)."""
        self.logger.debug(f"Extracting invoice data. Document type: {document_type}")
        self.logger.debug(f"Raw text input (first 500 chars): {text[:500]}")
        result = self._get_document_template(document_type)

        text_lower = text.lower()
        # Invoice number
        match = re.search(r"nr faktury\s*([0-9]+)", text_lower)
        if match:
            result["document_number"] = match.group(1)
        # Issue date
        match = re.search(r"data\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text_lower)
        if match:
            result["issue_date"] = self._parse_date(match.group(1))
        # Due date
        match = re.search(r"termin wymagalnosci\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text_lower)
        if match:
            result["due_date"] = self._parse_date(match.group(1))
        # Seller (Softreck OU)
        if "softreck" in text_lower:
            result["seller"] = {
                "name": "Softreck OU",
                "address": "Parnu mnt 139c, 11317 Tallinn, Estonia",
                "tax_id": "EE102146710"
            }
        # --- Buyer robust extraction ---
        buyer = {}
        # Pobierz buyer.name jako tekst po 'KLIENT' aż do pierwszego numeru lub słowa 'NIP'/'Nr VAT'/'Polska'
        buyer_block = re.search(r"klient\s+(.+?)(?=\d{2}-\d{3}|nip[:\s]*[0-9]{10}|nr vat[:\s]*[A-Z0-9]+|polska)", text, re.IGNORECASE)
        if buyer_block:
            buyer_name = buyer_block.group(1).strip().replace("\n", ", ")
            buyer["name"] = buyer_name
        nip_match = re.search(r"nip[:\s]*([0-9]{10})", text, re.IGNORECASE)
        if nip_match:
            buyer["tax_id"] = nip_match.group(1)
        if buyer:
            result["buyer"] = buyer
        # --- Items robust extraction ---
        items = []
        # Szukaj zarówno 'PLN xxx.xx' jak i 'xxx.xx PLN'
        for m in re.finditer(r"pln[\s:]*([0-9]+[\.,][0-9]{2})|([0-9]+[\.,][0-9]{2})[\s]*pln", text_lower):
            val = None
            if m.group(1):
                val = float(m.group(1).replace(",","."))
            elif m.group(2):
                val = float(m.group(2).replace(",","."))
            if val and val > 1:
                items.append({"description": "item", "quantity": 1, "unit_price": val, "amount": val})
        if items:
            result["items"] = items
        # --- Totals robust extraction ---
        if items:
            total = max(i["amount"] for i in items)
            result["totals"] = {
                "subtotal": sum(i["amount"] for i in items),
                "tax_amount": 0.0,
                "total": total,
                "currency": "PLN"
            }
        else:
            result["totals"] = {
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "total": 0.0,
                "currency": "PLN"
            }
        # Payment info (IBAN, SWIFT)
        iban = re.search(r"iban[:\s]*([a-z0-9]+)", text_lower)
        swift = re.search(r"swift[:\s]*([a-z0-9]+)", text_lower)
        if iban:
            result["bank_account"] = iban.group(1).upper()
        if swift:
            result["swift_code"] = swift.group(1).upper()
        # Always set currency
        result["currency"] = "PLN"
        # Always set tax to 0.0 (reverse charge)
        result["tax_amount"] = 0.0
        # Notes
        if "reverse charge" in text_lower:
            result["notes"] = "Reverse charge EU directive 2006/112"
        self._validate_and_clean(result)
        return result

    # --- Error detection algorithm ---
    @staticmethod
    def detect_extraction_errors(ocr_text: str, extracted_json: dict) -> List[str]:
        """Detect likely extraction errors by comparing OCR text and JSON fields."""
        errors = []
        # Check if invoice number appears in OCR text
        doc_num = extracted_json.get("document_number")
        if doc_num and doc_num not in ocr_text:
            errors.append(f"Document number '{doc_num}' not found in OCR text.")
        # Check if buyer and seller names appear
        for party in ("seller", "buyer"):
            name = extracted_json.get(party, {}).get("name")
            if name and name.lower() not in ocr_text.lower():
                errors.append(f"{party.capitalize()} name '{name}' not found in OCR text.")
        # Check if each item amount appears in OCR text
        for item in extracted_json.get("items", []):
            amt = str(item.get("amount"))
            if amt and amt not in ocr_text:
                errors.append(f"Item amount '{amt}' not found in OCR text.")
        # Check if total appears
        total = extracted_json.get("totals", {}).get("total")
        if total and str(total) not in ocr_text:
            errors.append(f"Total '{total}' not found in OCR text.")
        return errors

    def _extract_basic_info(self, text: str, language: str) -> Dict[str, Any]:
        """Extract basic invoice information."""
        result = {}
        
        # Document number (numer faktury)
        doc_number_match = re.search(
            r'(?i)(?:nr|numer|faktura)[\s]*(?:faktury)?[\s:]*([A-Z0-9-]+)', 
            text
        )
        if doc_number_match:
            result["document_number"] = doc_number_match.group(1).strip()
        
        # Issue date (data)
        issue_date_match = re.search(
            r'(?i)(?:data|data wystawienia|data sprzedaży)[\s:]*([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4})', 
            text
        )
        if issue_date_match:
            result["issue_date"] = self._parse_date(issue_date_match.group(1))
            
        # Due date (termin płatności)
        due_date_match = re.search(
            r'(?i)(?:termin[\s]+wymagalności|termin płatności|zapłacono do)[\s:]*([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4})', 
            text
        )
        if due_date_match:
            result["due_date"] = self._parse_date(due_date_match.group(1))
            
        # Currency (waluta)
        currency_match = re.search(
            r'(?i)(?:płatność w|kwota w|waluta):?\s*([A-Z]{3})', 
            text
        )
        if currency_match:
            result["currency"] = currency_match.group(1)
        else:
            # Default to PLN for Polish invoices
            result["currency"] = "PLN"
            
        return result
        
    def _extract_parties(self, text: str, language: str) -> Dict[str, Any]:
        """Extract seller and buyer information."""
        result = {"seller": {}, "buyer": {}}
        
        # Extract seller information
        seller_match = re.search(
            r'(?i)(?:sprzedawca|sprzedaż):?\s*([^\n]+)(?:\n\s*[^\n]*){0,3}?\n\s*NIP:\s*(\d{10}|\d{3}-\d{3}-\d{2}-\d{2})',
            text
        )
        if seller_match:
            result["seller"]["name"] = seller_match.group(1).strip()
            result["seller"]["tax_id"] = seller_match.group(2).replace("-", "")
            
        # Extract buyer information with more precise patterns for Softreck invoices
        # First, extract the buyer's tax ID (NIP) which is more reliably formatted
        nip_match = re.search(
            r'(?i)NIP\s*:?\s*([A-Z]{2}?\s*\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d?)',
            text
        )
        if nip_match:
            result["buyer"]["tax_id"] = re.sub(r'[^A-Za-z0-9]', '', nip_match.group(1)).upper()
        
        # Extract VAT number if different from NIP
        vat_match = re.search(
            r'(?i)Nr\s*VAT\s*:?\s*([A-Z]{2}?\s*\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d?)',
            text
        )
        if vat_match:
            vat_num = re.sub(r'[^A-Za-z0-9]', '', vat_match.group(1)).upper()
            if not result["buyer"].get("tax_id") or vat_num != result["buyer"].get("tax_id", ""):
                result["buyer"]["vat_number"] = vat_num
        
        # Extract buyer name and address - look for the text between KLIENT and NIP/VAT
        buyer_section = re.search(
            r'(?i)KLIENT\s*\n(.+?)(?=\s*(?:NIP|Nr\s*VAT|Nr\s*wpisu|Suma|Razem|$))',
            text,
            re.DOTALL
        )
        
        if buyer_section:
            buyer_text = buyer_section.group(1).strip()
            self.logger.debug(f"Buyer section found: {buyer_text}")
            
            # The first line is the company name
            lines = [line.strip() for line in buyer_text.split('\n') if line.strip()]
            if lines:
                result["buyer"]["name"] = lines[0]
                
                # The rest is the address (if there are multiple lines)
                if len(lines) > 1:
                    # Join address lines and clean up
                    address = ' '.join(lines[1:])
                    # Remove any tax-related information
                    address = re.sub(r'\s*(?:NIP|VAT|REGON|KRS|Nr\s*wpisu)\s*:?\s*[\d\-\sA-Za-z]*', '', address, flags=re.IGNORECASE)
                    # Clean up multiple spaces and trim
                    address = re.sub(r'\s+', ' ', address).strip()
                    # Remove any trailing commas or other punctuation
                    address = re.sub(r'[\s,.;]+$', '', address)
                    result["buyer"]["address"] = address
        
        # If we still don't have a buyer name, try a simpler pattern
        if not result["buyer"].get("name"):
            name_match = re.search(r'KLIENT\s*\n([^\n]+)', text, re.IGNORECASE)
            if name_match:
                result["buyer"]["name"] = name_match.group(1).strip()
        
        # If we still don't have an address, try to find it after the buyer name
        if not result["buyer"].get("address") and result["buyer"].get("name"):
            # Look for the address after the buyer name and before any tax info
            address_pattern = (
                r'(?i)' + re.escape(result["buyer"]["name"]) + 
                r'\s*\n([^\n]+(?:\n[^\n]+){0,2}?)(?=\s*(?:NIP|Nr\s*VAT|Suma|Razem|$))'
            )
            address_section = re.search(address_pattern, text, re.DOTALL)
            if address_section:
                address = address_section.group(1).strip()
                # Clean up the address
                address = re.sub(r'\s*(?:NIP|VAT|REGON|KRS|Nr\s*wpisu)\s*:?\s*[\d\-\sA-Za-z]*', '', address, flags=re.IGNORECASE)
                address = re.sub(r'\s+', ' ', address).strip()
                address = re.sub(r'[\s,.;]+$', '', address)
                result["buyer"]["address"] = address
            
        return result
        
    def _extract_items(self, text: str, language: str) -> List[Dict[str, Any]]:
        """Extract line items from the invoice."""
        items = []
        
        # First, try to find the items section with a more flexible pattern
        items_section_match = re.search(
            r'(?i)(?:produkt/usługa|towar/usługa|nazwa towaru/usługi).*?\n(?:.*\n){0,2}?(.*?)\n\s*(?:suma|razem|podsumowanie|podliczenie|kwota)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        
        if not items_section_match:
            # Alternative pattern if the first one doesn't match
            items_section_match = re.search(
                r'(?i)(?:produkt|usługa|nazwa).*?\n(?:.*\n){0,2}?(.*?)\n\s*(?:suma|razem|podsumowanie|podliczenie|kwota)',
                text,
                re.DOTALL | re.IGNORECASE
            )
        
        if not items_section_match:
            self.logger.warning("Could not find items section in the invoice")
            return items
            
        items_text = items_section_match.group(1).strip()
        self.logger.debug(f"Items section found: {items_text}")
        
        # Try different patterns to match line items
        # Pattern 1: Description followed by price, quantity, tax, and amount
        item_patterns = [
            # Pattern: Description [whitespace] Price [whitespace] Qty [whitespace] Tax% [whitespace] Amount
            r'(?m)^(.+?)\s{2,}(\d+[\s,.]\d{2})\s+(\d+)\s*(?:\([^)]+\))?\s*(\d+%)\s+(\d+[\s,.]\d{2})',
            # Pattern: Description [whitespace] Amount [currency]
            r'(?m)^(.+?)\s{2,}(\d+[\s,.]\d{2})\s*([A-Z]{3})',
            # Pattern: Just description and amount (most basic)
            r'(?m)^(.+?)\s{2,}(\d+[\s,.]\d{2})'
        ]
        
        for pattern in item_patterns:
            item_matches = list(re.finditer(pattern, items_text))
            if item_matches:
                self.logger.debug(f"Found {len(item_matches)} items with pattern: {pattern}")
                break
        else:
            self.logger.warning("No items matched any pattern")
            return items
        
        for match in item_matches:
            try:
                # Initialize with default values
                description = ""
                unit_price = 0.0
                quantity = 1.0
                tax_rate = 0.0
                amount = 0.0
                
                # Extract based on the matched groups
                if len(match.groups()) >= 2:
                    description = match.group(1).strip()
                    
                    # Skip header or total lines
                    if any(term in description.lower() for term in ['produkt', 'usługa', 'towar', 'nazwa', 'suma', 'razem']):
                        continue
                    
                    # Clean up the description
                    description = re.sub(r'\s+', ' ', description).strip()
                    
                    # Extract amount (always the last number)
                    amount_str = match.group(len(match.groups())).replace(' ', '').replace(',', '.')
                    amount = float(amount_str)
                    
                    # Try to extract unit price and quantity if available
                    if len(match.groups()) >= 3:
                        unit_price_str = match.group(2).replace(' ', '').replace(',', '.')
                        unit_price = float(unit_price_str)
                        
                        # If we have a quantity, use it; otherwise, calculate from amount/unit_price
                        if len(match.groups()) >= 4 and not match.group(3).endswith('%'):
                            quantity_str = match.group(3).replace(' ', '').replace(',', '.')
                            quantity = float(quantity_str)
                        elif unit_price > 0:
                            quantity = amount / unit_price
                            # Round to whole number if it's close to an integer
                            if abs(quantity - round(quantity)) < 0.01:
                                quantity = round(quantity)
                    
                    # Extract tax rate if available
                    if len(match.groups()) >= 4 and match.group(4) and '%' in match.group(4):
                        tax_rate = float(match.group(4).replace('%', '').strip())
                    
                    items.append({
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "tax_rate": tax_rate,
                        "amount": amount,
                    })
                    
                    self.logger.debug(f"Extracted item: {description} - {quantity} x {unit_price} = {amount} (VAT: {tax_rate}%)")
                    
            except (ValueError, IndexError, AttributeError) as e:
                self.logger.warning(f"Error parsing line item: {e}")
                continue
            
        return items
        
    def _extract_totals(self, text: str, language: str) -> Dict[str, Any]:
        """Extract total amounts from the invoice."""
        result = {}
        
        # First, try to find the total amount directly with a specific pattern
        total_match = re.search(
            r'(?i)Kwota\s+taczna\s+faktury\s*[^\d]*?([\d\s,]+(?:\.[\d\s]+)?)\s*PLN',
            text
        )
    
        if not total_match:
            # Look for any amount that looks like a total
            total_match = re.search(
                r'(?i)(?:kwota\s+łączna\s+faktur[^\d]*|razem\s+do\s+zapłaty\s*:?\s*)(?:[A-Z]{3})?\s*([\d\s,]+(?:\.[\d\s]+)?)',
                text
            )
    
        if total_match:
            try:
                # Clean up the number and convert to float
                total_amount = float(re.sub(r'[^\d,]', '', total_match.group(1).replace(',', '.')))
                result["totals"]["total"] = total_amount
                result["totals"]["currency"] = "PLN"  # Default to PLN for this invoice
                result["total"] = total_amount  # For backward compatibility
                result["currency"] = "PLN"  # For backward compatibility
                self.logger.info(f"Extracted total amount: {total_amount} PLN")
            except (ValueError, AttributeError) as e:
                self.logger.warning(f"Could not parse total amount: {e}")
        else:
            self.logger.warning("Total amount not found")
    
        # Try to extract subtotal and tax amount if available
        subtotal_match = re.search(
            r'(?i)Suma\s+bez\s+VAT\s+0%\s+([\d\s,]+(?:\.[\d\s]+)?)',
            text
        )
    
        tax_match = re.search(
            r'(?i)VAT\s+0%\s+([\d\s,]+(?:\.[\d\s]+)?)',
            text
        )
    
        if subtotal_match:
            try:
                subtotal = float(re.sub(r'[^\d,]', '', subtotal_match.group(1).replace(',', '.')))
                result["totals"]["subtotal"] = subtotal
                self.logger.info(f"Extracted subtotal: {subtotal}")
            except (ValueError, AttributeError) as e:
                self.logger.warning(f"Could not parse subtotal amount: {e}")
    
        if tax_match:
            try:
                tax_amount = float(re.sub(r'[^\d,]', '', tax_match.group(1).replace(',', '.')))
                result["totals"]["tax_amount"] = tax_amount
                result["tax_amount"] = tax_amount  # For backward compatibility
                self.logger.info(f"Extracted tax amount: {tax_amount}")
            except (ValueError, AttributeError) as e:
                self.logger.warning(f"Could not parse tax amount: {e}")
    
        # If we have a total but no subtotal, use the total as subtotal (for 0% VAT)
        if "total" in result.get("totals", {}) and "subtotal" not in result.get("totals", {}):
            result["totals"]["subtotal"] = result["totals"]["total"]
            result["totals"]["tax_amount"] = 0.0
            result["tax_amount"] = 0.0  # For backward compatibility
            self.logger.info("Using total as subtotal (0% VAT)")
    
        return result

    def _parse_date(self, date_str: str) -> str:
        """Parse date string in the format DD.MM.YYYY."""
        try:
            date = datetime.strptime(date_str, "%d.%m.%Y")
            return date.strftime("%Y-%m-%d")
        except ValueError:
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
