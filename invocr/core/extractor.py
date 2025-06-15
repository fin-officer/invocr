"""
Advanced data extraction from OCR text
Supports multiple document types and languages
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from dateutil import parser as date_parser

from ..utils.config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DataExtractor:
    """Advanced data extractor for invoices, receipts, and payment documents"""

    def __init__(self, languages: List[str] = None):
        self.languages = languages or ["en", "pl", "de", "fr", "es"]
        self.patterns = self._load_extraction_patterns()
        logger.info(f"Data extractor initialized for languages: {self.languages}")

    def extract_invoice_data(
        self, text: str, document_type: str = "invoice"
    ) -> Dict[str, any]:
        """
        Extract structured data from invoice text

        Args:
            text: Raw text from OCR
            document_type: Type of document (invoice, receipt, payment)

        Returns:
            Structured data dictionary
        """
        # Detect language for better pattern matching
        detected_lang = self._detect_language(text)

        # Initialize data structure based on document type
        data = self._get_document_template(document_type)

        # Extract basic information
        data.update(self._extract_basic_info(text, detected_lang))

        # Extract parties (seller/buyer)
        data.update(self._extract_parties(text, detected_lang))

        # Extract items/services
        data["items"] = self._extract_items(text, detected_lang)

        # Extract financial totals
        data["totals"] = self._extract_totals(text, detected_lang)

        # Extract payment information
        data.update(self._extract_payment_info(text, detected_lang))

        # Validate and clean data
        self._validate_and_clean(data)

        # Add metadata
        data["_metadata"] = {
            "document_type": document_type,
            "detected_language": detected_lang,
            "extraction_timestamp": datetime.now().isoformat(),
            "text_length": len(text),
            "confidence": self._calculate_confidence(data, text),
        }

        return data

    def _get_document_template(self, doc_type: str) -> Dict[str, any]:
        """Get base template for different document types"""
        templates = {
            "invoice": {
                "document_number": "",
                "document_date": "",
                "due_date": "",
                "seller": {
                    "name": "",
                    "address": "",
                    "tax_id": "",
                    "phone": "",
                    "email": "",
                },
                "buyer": {
                    "name": "",
                    "address": "",
                    "tax_id": "",
                    "phone": "",
                    "email": "",
                },
                "items": [],
                "totals": {
                    "subtotal": 0.0,
                    "tax_rate": 0.0,
                    "tax_amount": 0.0,
                    "total": 0.0,
                },
                "payment_method": "",
                "bank_account": "",
                "notes": "",
            },
            "receipt": {
                "receipt_number": "",
                "date": "",
                "time": "",
                "merchant": {"name": "", "address": "", "phone": ""},
                "items": [],
                "totals": {"subtotal": 0.0, "tax": 0.0, "total": 0.0},
                "payment_method": "",
                "card_info": "",
            },
            "payment": {
                "transaction_id": "",
                "date": "",
                "payer": {"name": "", "account": ""},
                "payee": {"name": "", "account": ""},
                "amount": 0.0,
                "currency": "",
                "description": "",
                "reference": "",
            },
        }
        return templates.get(doc_type, templates["invoice"])

    def _extract_basic_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract basic document information"""
        result = {}
        patterns = self.patterns[language]["basic"]

        # Document number
        for pattern in patterns["document_number"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result["document_number"] = match.group(1).strip()
                break

        # Dates
        dates = self._extract_dates(text)
        if dates:
            result["document_date"] = dates[0]
            if len(dates) > 1:
                result["due_date"] = dates[1]
            elif "document_date" in result:
                # Calculate due date (30 days default)
                try:
                    doc_date = datetime.strptime(dates[0], "%Y-%m-%d")
                    due_date = doc_date + timedelta(days=30)
                    result["due_date"] = due_date.strftime("%Y-%m-%d")
                except:
                    pass

        return result

    def _extract_parties(self, text: str, language: str) -> Dict[str, Dict]:
        """Extract seller and buyer information"""
        parties = {"seller": {}, "buyer": {}}

        # Split text into potential sections
        sections = self._split_into_sections(text)

        # Extract TAX IDs first (helps identify parties)
        tax_ids = self._extract_tax_ids(text)

        # Extract names and addresses
        names_addresses = self._extract_names_addresses(text, language)

        # Extract contact info
        emails = self._extract_emails(text)
        phones = self._extract_phones(text)

        # Assign to seller/buyer (first = seller, second = buyer typically)
        if len(names_addresses) >= 1:
            parties["seller"].update(names_addresses[0])
        if len(names_addresses) >= 2:
            parties["buyer"].update(names_addresses[1])

        if len(tax_ids) >= 1:
            parties["seller"]["tax_id"] = tax_ids[0]
        if len(tax_ids) >= 2:
            parties["buyer"]["tax_id"] = tax_ids[1]

        if len(emails) >= 1:
            parties["seller"]["email"] = emails[0]
        if len(emails) >= 2:
            parties["buyer"]["email"] = emails[1]

        if len(phones) >= 1:
            parties["seller"]["phone"] = phones[0]
        if len(phones) >= 2:
            parties["buyer"]["phone"] = phones[1]

        return parties

    def _extract_items(self, text: str, language: str) -> List[Dict]:
        """Extract line items from text"""
        items = []
        patterns = self.patterns[language]["items"]

        # Look for table-like structures
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try different item patterns
            for pattern in patterns["line_item"]:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        item = self._parse_item_match(match, pattern)
                        if item and item.get("description"):
                            items.append(item)
                            break
                    except:
                        continue

        return items

    def _parse_item_match(self, match, pattern: str) -> Optional[Dict]:
        """Parse regex match into item dictionary"""
        groups = match.groups()

        # Different patterns have different group arrangements
        if len(groups) >= 4:
            try:
                return {
                    "description": groups[0].strip() if groups[0] else "",
                    "quantity": float(groups[1].replace(",", ".")) if groups[1] else 1,
                    "unit_price": (
                        float(groups[2].replace(",", ".")) if groups[2] else 0
                    ),
                    "total_price": (
                        float(groups[3].replace(",", ".")) if groups[3] else 0
                    ),
                }
            except (ValueError, IndexError):
                return None

        return None

    def _extract_totals(self, text: str, language: str) -> Dict[str, float]:
        """Extract financial totals"""
        totals = {"subtotal": 0.0, "tax_rate": 23.0, "tax_amount": 0.0, "total": 0.0}
        patterns = self.patterns[language]["totals"]

        # Extract different total types
        for total_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    try:
                        value_str = match.group(1).replace(" ", "").replace(",", ".")
                        value = float(re.sub(r"[^\d\.]", "", value_str))
                        totals[total_type] = value
                        break
                    except (ValueError, IndexError):
                        continue

        # Calculate missing values
        if totals["total"] > 0 and totals["subtotal"] == 0:
            # Estimate subtotal from total
            totals["subtotal"] = totals["total"] / (1 + totals["tax_rate"] / 100)
            totals["tax_amount"] = totals["total"] - totals["subtotal"]

        return totals

    def _extract_payment_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract payment method and bank account info"""
        result = {}
        patterns = self.patterns[language]["payment"]

        # Payment method
        for pattern in patterns["payment_method"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["payment_method"] = match.group(1).strip()
                break

        # Bank account
        for pattern in patterns["bank_account"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["bank_account"] = match.group(1).strip()
                break

        return result

    def _extract_dates(self, text: str) -> List[str]:
        """Extract and parse dates from text"""
        date_patterns = [
            r"(\d{1,2}[\-\./]\d{1,2}[\-\./]\d{4})",
            r"(\d{4}[\-\./]\d{1,2}[\-\./]\d{1,2})",
            r"(\d{1,2}\s+\w+\s+\d{4})",
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    parsed_date = date_parser.parse(match, dayfirst=True)
                    date_str = parsed_date.strftime("%Y-%m-%d")
                    if date_str not in dates:
                        dates.append(date_str)
                except:
                    continue

        return sorted(dates)

    def _extract_tax_ids(self, text: str) -> List[str]:
        """Extract tax identification numbers"""
        patterns = [
            r"(?:NIP|VAT|Tax\s*ID)[:\s]*([0-9\-\s]{8,15})",
            r"([0-9]{3}[\-\s]?[0-9]{3}[\-\s]?[0-9]{2}[\-\s]?[0-9]{2})",
            r"([0-9]{2}[\-\s]?[0-9]{8})",
        ]

        tax_ids = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean_id = re.sub(r"[\-\s]", "", match)
                if len(clean_id) >= 8 and clean_id not in tax_ids:
                    tax_ids.append(match.strip())

        return tax_ids

    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses"""
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        return list(set(re.findall(pattern, text)))

    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers"""
        patterns = [
            r"(?:\+48\s?)?(?:\d{2,3}[\s\-]?\d{3}[\s\-]?\d{2,3}[\s\-]?\d{2,3})",
            r"(?:\+\d{1,3}\s?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}",
        ]

        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)

        return list(set(phones))

    def _extract_names_addresses(self, text: str, language: str) -> List[Dict]:
        """Extract company names and addresses"""
        # This is a simplified implementation
        # In practice, you'd use NER (Named Entity Recognition) or more sophisticated methods

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Look for patterns that indicate company names/addresses
        entities = []
        current_entity = {"name": "", "address": ""}

        for line in lines:
            # Skip obvious non-entity lines
            if any(
                word in line.lower() for word in ["faktura", "invoice", "total", "suma"]
            ):
                continue

            # Simple heuristic: lines with proper case might be names/addresses
            if len(line) > 5 and any(c.isupper() for c in line):
                if not current_entity["name"]:
                    current_entity["name"] = line
                else:
                    current_entity["address"] += line + " "

                # If we have enough info, save entity
                if len(current_entity["address"]) > 20:
                    entities.append(
                        {
                            "name": current_entity["name"],
                            "address": current_entity["address"].strip(),
                        }
                    )
                    current_entity = {"name": "", "address": ""}

        return entities[:2]  # Return max 2 entities

    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into logical sections"""
        # Split by multiple newlines or obvious section breaks
        sections = re.split(r"\n\s*\n|\n-+\n|\n=+\n", text)
        return [section.strip() for section in sections if section.strip()]

    def _detect_language(self, text: str) -> str:
        """Simple language detection"""
        # Check for language-specific characters and words
        lang_indicators = {
            "pl": [
                "ą",
                "ć",
                "ę",
                "ł",
                "ń",
                "ó",
                "ś",
                "ź",
                "ż",
                "faktura",
                "sprzedawca",
            ],
            "de": ["ä", "ö", "ü", "ß", "rechnung", "verkäufer"],
            "fr": ["à", "â", "é", "è", "ê", "facture", "vendeur"],
            "es": ["ñ", "á", "é", "í", "ó", "ú", "factura", "vendedor"],
            "it": ["à", "è", "ì", "ò", "ù", "fattura", "venditore"],
        }

        text_lower = text.lower()
        scores = {}

        for lang, indicators in lang_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            scores[lang] = score

        detected = max(scores.keys(), key=lambda k: scores[k]) if scores else "en"
        return detected if scores[detected] > 0 else "en"

    def _validate_and_clean(self, data: Dict) -> None:
        """Validate and clean extracted data"""
        # Clean numeric values
        if "totals" in data:
            for key, value in data["totals"].items():
                if isinstance(value, str):
                    try:
                        data["totals"][key] = float(value.replace(",", "."))
                    except ValueError:
                        data["totals"][key] = 0.0

        # Clean whitespace in text fields
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value.strip()
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, str):
                        value[subkey] = subvalue.strip()

    def _calculate_confidence(self, data: Dict, text: str) -> float:
        """Calculate extraction confidence score"""
        score = 0
        max_score = 10

        # Check for key fields
        if data.get("document_number"):
            score += 2
        if data.get("document_date"):
            score += 1
        if data.get("seller", {}).get("name"):
            score += 1
        if data.get("items") and len(data["items"]) > 0:
            score += 2
        if data.get("totals", {}).get("total", 0) > 0:
            score += 2
        if data.get("seller", {}).get("tax_id"):
            score += 1
        if data.get("payment_method"):
            score += 1

        return min(score / max_score, 1.0)

    def _load_extraction_patterns(self) -> Dict[str, Dict]:
        """Load regex patterns for different languages"""
        return {
            "en": {
                "basic": {
                    "document_number": [
                        r"(?:Invoice|INV)\s*[:#]?\s*([A-Z0-9\/\-\.]+)",
                        r"(?:Number|No\.?)\s*:?\s*([A-Z0-9\/\-\.]+)",
                    ]
                },
                "totals": {
                    "total": [
                        r"(?:Total|TOTAL|Amount Due)\s*:?\s*([0-9\s,]+\.?\d{0,2})"
                    ],
                    "subtotal": [
                        r"(?:Subtotal|Sub-total)\s*:?\s*([0-9\s,]+\.?\d{0,2})"
                    ],
                    "tax_amount": [r"(?:Tax|VAT)\s*:?\s*([0-9\s,]+\.?\d{0,2})"],
                },
                "items": {
                    "line_item": [
                        r"(.+?)\s+(\d+(?:\.\d+)?)\s+([0-9,]+\.?\d{2})\s+([0-9,]+\.?\d{2})"
                    ]
                },
                "payment": {
                    "payment_method": [r"(?:Payment|Method)\s*:?\s*([A-Za-z\s]+)"],
                    "bank_account": [r"(?:Account|IBAN)\s*:?\s*([A-Z0-9\s]+)"],
                },
            },
            "pl": {
                "basic": {
                    "document_number": [
                        r"(?:Faktura|FV|F)\s*[:/]?\s*([A-Z0-9\/\-\.]+)",
                        r"(?:Nr\.?|Numer)\s*:?\s*([A-Z0-9\/\-\.]+)",
                    ]
                },
                "totals": {
                    "total": [
                        r"(?:Razem|Do zapłaty|Suma)\s*:?\s*([0-9\s,]+[,\.]\d{2})\s*(?:zł|PLN)?"
                    ],
                    "subtotal": [r"(?:Netto|Suma netto)\s*:?\s*([0-9\s,]+[,\.]\d{2})"],
                    "tax_amount": [r"(?:VAT|Podatek)\s*:?\s*([0-9\s,]+[,\.]\d{2})"],
                },
                "items": {
                    "line_item": [
                        r"(.+?)\s+(\d+(?:[,\.]\d+)?)\s+([0-9\s,]+[,\.]\d{2})\s+([0-9\s,]+[,\.]\d{2})",
                        r"(\d+)\s+(.+?)\s+(\d+(?:[,\.]\d+)?)\s+([0-9\s,]+[,\.]\d{2})\s+([0-9\s,]+[,\.]\d{2})",
                    ]
                },
                "payment": {
                    "payment_method": [
                        r"(?:Sposób płatności|Płatność)\s*:?\s*([A-Za-z\s]+)"
                    ],
                    "bank_account": [r"(?:Nr konta|Konto|IBAN)\s*:?\s*([A-Z0-9\s]+)"],
                },
            },
            "de": {
                "basic": {
                    "document_number": [
                        r"(?:Rechnung|RG)\s*[:\-]?\s*([A-Z0-9\/\-\.]+)",
                        r"(?:Nummer|Nr\.?)\s*:?\s*([A-Z0-9\/\-\.]+)",
                    ]
                },
                "totals": {
                    "total": [
                        r"(?:Gesamt|Gesamtbetrag|Endbetrag)\s*:?\s*([0-9\s,]+[,\.]\d{2})\s*€?"
                    ],
                    "subtotal": [
                        r"(?:Netto|Zwischensumme)\s*:?\s*([0-9\s,]+[,\.]\d{2})"
                    ],
                    "tax_amount": [r"(?:MwSt|Steuer)\s*:?\s*([0-9\s,]+[,\.]\d{2})"],
                },
                "items": {
                    "line_item": [
                        r"(.+?)\s+(\d+(?:[,\.]\d+)?)\s+([0-9\s,]+[,\.]\d{2})\s+([0-9\s,]+[,\.]\d{2})"
                    ]
                },
                "payment": {
                    "payment_method": [r"(?:Zahlungsart|Zahlung)\s*:?\s*([A-Za-z\s]+)"],
                    "bank_account": [r"(?:Kontonummer|IBAN)\s*:?\s*([A-Z0-9\s]+)"],
                },
            },
        }


def create_extractor(languages: List[str] = None) -> DataExtractor:
    """Factory function to create data extractor instance"""
    return DataExtractor(languages)
