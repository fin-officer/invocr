"""
Data extraction from invoice text
Simplified version focusing on invoice data extraction
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataExtractor:
    """
    Data extractor for invoice documents.
    Supports multiple languages and various invoice formats.
    """

    def __init__(self, languages: List[str] = None):
        """
        Initialize the DataExtractor with specified languages.

        Args:
            languages: List of language codes to support (default: ["en", "pl"])
        """
        self.languages = languages or ["en", "pl"]
        # self.patterns = self._load_extraction_patterns()  # Removed: now handled by modular extractors
        logger.info(f"Data extractor initialized for languages: {self.languages}")

    def extract_invoice_data(
        self, text: str, document_type: str = "invoice"
    ) -> Dict[str, Any]:
        """
        Extract structured data from invoice text.

        Args:
            text: Raw text from OCR
            document_type: Type of document (e.g., "invoice", "receipt")

        Returns:
            Dict containing structured invoice data
        """
        # Initialize data structure
        data = self._get_document_template(document_type)

        # Detect document language
        detected_lang = self._detect_language(text)

        # Extract basic information
        data.update(self._extract_basic_info(text, detected_lang))

        # Extract parties (seller/buyer)
        data.update(self._extract_parties(text, detected_lang))

        # Extract items and totals
        data["items"] = self._extract_items(text, detected_lang)
        data["totals"] = self._extract_totals(text, detected_lang)

        # Extract payment information
        payment_info = self._extract_payment_info(text, detected_lang)
        data.update(payment_info)

        # Add metadata
        data["_metadata"] = {
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "document_type": document_type,
            "language": detected_lang,
            "confidence": self._calculate_confidence(data, text),
        }

        # Clean and validate the extracted data
        data = self._clean_and_validate_data(data)

        return data

    def _get_document_template(self, doc_type: str) -> Dict[str, Any]:
        """
        Get base template for different document types.

        Args:
            doc_type: Type of document (e.g., "invoice", "receipt", "payment")

        Returns:
            Dictionary with the document template structure
        """
        templates = {
            "invoice": {
                "document_type": "invoice",
                "document_number": "",
                "issue_date": "",
                "due_date": "",
                "seller": {
                    "name": "",
                    "address": "",
                    "tax_id": "",
                    "email": "",
                    "phone": "",
                },
                "buyer": {"name": "", "address": "", "tax_id": ""},
                "items": [],
                "totals": {
                    "subtotal": 0.0,
                    "tax_amount": 0.0,
                    "total": 0.0,
                    "currency": "",
                },
                "payment_terms": "",
                "payment_method": "",
                "bank_account": "",
                "notes": "",
            },
            "receipt": {
                "document_type": "receipt",
                "document_number": "",
                "date": "",
                "seller": {"name": "", "tax_id": ""},
                "items": [],
                "totals": {
                    "subtotal": 0.0,
                    "tax_amount": 0.0,
                    "total": 0.0,
                    "currency": "",
                    "payment_method": "",
                },
            },
            "payment": {
                "document_type": "payment",
                "document_number": "",
                "date": "",
                "amount": 0.0,
                "currency": "",
                "payer": {"name": "", "account": ""},
                "recipient": {"name": "", "account": ""},
                "reference": "",
                "payment_method": "",
                "notes": "",
            },
        }

        return templates.get(doc_type, {"document_type": doc_type})

    def _detect_language(self, text: str) -> str:
        """
        Detect the language of the document text.

        Args:
            text: Document text to analyze

        Returns:
            Detected language code (e.g., 'en', 'pl')
        """
        text_lower = text.lower()
        logger.info(f"[DataExtractor] Language detection input (first 500 chars): {text_lower[:500]}")
        if (
            "softreck" in text_lower or
            "faktura" in text_lower or
            "nip" in text_lower or
            "sprzedawca" in text_lower or
            "klient" in text_lower or
            "polska" in text_lower or
            "vat:" in text_lower or
            "reverse charge" in text_lower or
            "pln" in text_lower
        ):
            logger.info("[DataExtractor] Detected language: pl")
            return "pl"
        logger.info("[DataExtractor] Detected language: en")
        return "en"

    def _extract_basic_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract basic document information"""
        result = {}
        raise NotImplementedError(
            "Basic info extraction must be implemented in a language-specific extractor."
        )

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
        patterns = self.patterns[language]

        # Extract seller and buyer sections
        for party_type in ["seller", "buyer"]:
            for pattern in patterns.get("parties", {}).get(party_type, []):
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    party_text = match.group(1).strip()
                    # Extract name (first line)
                    name = party_text.split("\n")[0].strip()
                    parties[party_type]["name"] = name

                    # Extract address (remaining lines)
                    address_lines = [
                        line.strip()
                        for line in party_text.split("\n")[1:]
                        if line.strip()
                    ]
                    parties[party_type]["address"] = " ".join(address_lines)
                    break

        # Extract contact info
        for party_type in ["seller", "buyer"]:
            if party_type in parties:
                # Extract email
                if "email" not in parties[party_type]:
                    email_matches = re.findall(
                        patterns["contact"]["email"][0], text, re.IGNORECASE
                    )
                    if email_matches:
                        parties[party_type]["email"] = email_matches[0]

                # Extract tax ID
                if "tax_id" not in parties[party_type]:
                    for pattern in patterns["contact"]["tax_id"]:
                        tax_match = re.search(pattern, text, re.IGNORECASE)
                        if tax_match:
                            parties[party_type]["tax_id"] = tax_match.group(1).strip()
                            break

        return parties

    def _extract_items(self, text: str, language: str) -> List[Dict]:
        """Extract line items from text"""
        items = []
        raise NotImplementedError(
            "Item extraction must be implemented in a language-specific extractor."
        )

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
        raise NotImplementedError(
            "Totals extraction must be implemented in a language-specific extractor."
        )

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
        raise NotImplementedError(
            "Payment info extraction must be implemented in a language-specific extractor."
        )

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
        """
        Calculate confidence score for the extracted data.

        Args:
            data: Extracted data dictionary
            text: Original text used for extraction

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0
        max_score = 10  # Total possible score

        # Basic document info
        if data.get("document_number"):
            score += 2
        if data.get("issue_date"):
            score += 1

        # Seller information
        seller = data.get("seller", {})
        if seller.get("name"):
            score += 1
        if seller.get("tax_id") or seller.get("address"):
            score += 1

        # Buyer information
        buyer = data.get("buyer", {})
        if buyer.get("name"):
            score += 1
        if buyer.get("tax_id") or buyer.get("address"):
            score += 1

        # Items and totals
        if data.get("items") and len(data["items"]) > 0:
            score += 2
        if data.get("totals", {}).get("total", 0) > 0:
            score += 2

        # Payment information
        if data.get("payment_method") or data.get("bank_account"):
            score += 1

        # Payment information
        if data.get("payment_method") or data.get("bank_account"):
            score += 1

        # Calculate final score (normalized to 0.0-1.0)
        return min(score / max_score, 1.0)


def create_extractor(languages: List[str] = None, **kwargs) -> DataExtractor:
    """
    Factory function to create data extractor instance.
    Dynamically selects the appropriate language-specific extractor.

    Args:
        languages (List[str], optional): List of languages to support. Defaults to None.

    Returns:
        DataExtractor: Data extractor instance (language-specific).
    """
    # Import language-specific extractors from the extractors package
    from invocr.extractors.de.extractor import GermanExtractor
    from invocr.extractors.en.extractor import EnglishExtractor
    from invocr.extractors.pl.extractor import PolishExtractor
    from invocr.extractors.es.extractor import SpanishExtractor
    from invocr.extractors.fr.extractor import FrenchExtractor

    # Default to English if no languages specified
    if not languages:
        languages = ["en"]

    # Check for special document formats first by examining content patterns 
    def detect_document_format(text):
        # Look for Adobe invoice specific patterns
        adobe_patterns = [
            r'Adobe Systems Software Ireland',
            r'Adobe.*Invoice',
            r'Invoice Number.*?\d+',
            r'PRODUCT NUMBER.*PRODUCT DESCRIPTION',
            r'GRAND TO[TU]AL',  # Handle both TOTAL and TOUAL (typo)
        ]
        
        # Count matches for Adobe patterns
        adobe_score = sum(1 for pattern in adobe_patterns if re.search(pattern, text or "", re.IGNORECASE))
        
        logger.info(f"[FormatDetector] Adobe score: {adobe_score}/5")
        
        # If we have strong Adobe patterns, use the specialized extractor
        if adobe_score >= 2:
            logger.info(f"[FormatDetector] Detected Adobe invoice format (score: {adobe_score}/5)")
            return "adobe"
        
        return None
    
    # Select extractor based on content and language
    # If sample_text is provided, use it for format detection
    sample_text = kwargs.get("sample_text")
    if sample_text:
        # Try to detect document format first
        doc_format = detect_document_format(sample_text)
        
        if doc_format == "adobe":
            from invocr.extractors.specialized.adobe_extractor import AdobeInvoiceExtractor
            logger.info(f"[ExtractorFactory] Using specialized AdobeInvoiceExtractor")
            return AdobeInvoiceExtractor(ocr_text=sample_text)
    
    # If no special format detected, select by language
    primary_lang = languages[0].lower()

    if primary_lang == "pl":
        logger.info(f"[ExtractorFactory] Using PolishExtractor for languages={languages}")
        return PolishExtractor(languages)
    elif primary_lang == "de":
        logger.info(f"[ExtractorFactory] Using GermanExtractor for languages={languages}")
        return GermanExtractor(languages)
    elif primary_lang == "es":
        logger.info(f"[ExtractorFactory] Using SpanishExtractor for languages={languages}")
        return SpanishExtractor(languages)
    elif primary_lang == "fr":
        logger.info(f"[ExtractorFactory] Using FrenchExtractor for languages={languages}")
        return FrenchExtractor(languages)
    else:
        logger.info(f"[ExtractorFactory] Using EnglishExtractor for languages={languages}")
        return EnglishExtractor(languages)
