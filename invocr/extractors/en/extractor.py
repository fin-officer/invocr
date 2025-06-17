"""
English language extractor implementation.
"""
from typing import Any, Dict, List, Optional
import re
from datetime import datetime

from ..base import DataExtractor


class EnglishExtractor(DataExtractor):
    """English language extractor implementation."""

    def _extract_basic_info(self, text: str, language: str) -> Dict[str, Any]:
        """Extract basic invoice information."""
        result = {}
        # Simple patterns for basic info extraction
        patterns = {
            "document_number": [
                r"(?:Invoice|Bill|Receipt)\s*[#:]?\s*([A-Z0-9-]+)",
                r"(?:No\.?|Number|Nr\.?)\s*[:#]?\s*([A-Z0-9-]+)"
            ],
            "issue_date": [
                r"(?:Date|Dated|Issued?)\s*[:]?\s*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})",
                r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
            ],
            "due_date": [
                r"(?:Due|Payment Due|Due Date)\s*[:]?\s*([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})",
                r"Due:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})"
            ]
        }

        # Extract document number
        for pattern in patterns["document_number"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["document_number"] = match.group(1).strip()
                break

        # Extract dates
        for date_field, date_patterns in [("issue_date", patterns["issue_date"]), 
                                        ("due_date", patterns["due_date"])]:
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        date_str = match.group(1).strip()
                        # Try to parse the date (simplified)
                        date_obj = datetime.strptime(date_str, "%d/%m/%Y")  # Try common format first
                        result[date_field] = date_obj.strftime("%Y-%m-%d")
                        break
                    except (ValueError, IndexError):
                        continue

        return result

    def _extract_parties(self, text: str, language: str) -> Dict[str, Dict[str, str]]:
        """Extract seller and buyer information."""
        return {
            "seller": {"name": "", "address": "", "tax_id": ""},
            "buyer": {"name": "", "address": "", "tax_id": ""}
        }

    def _extract_items(self, text: str, language: str) -> List[Dict[str, Any]]:
        """Extract line items from the document."""
        return []

    def _extract_totals(self, text: str, language: str) -> Dict[str, float]:
        """Extract financial totals."""
        return {"subtotal": 0.0, "tax_amount": 0.0, "total": 0.0}

    def _extract_payment_info(self, text: str, language: str) -> Dict[str, str]:
        """Extract payment method and bank account info."""
        return {}

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
