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
        self.patterns = self._load_extraction_patterns()
        logger.info(f"Data extractor initialized for languages: {self.languages}")

    def extract_invoice_data(self, text: str, document_type: str = "invoice") -> Dict[str, Any]:
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
            "confidence": self._calculate_confidence(data, text)
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
                    "phone": ""
                },
                "buyer": {
                    "name": "",
                    "address": "",
                    "tax_id": ""
                },
                "items": [],
                "totals": {
                    "subtotal": 0.0,
                    "tax_amount": 0.0,
                    "total": 0.0,
                    "currency": ""
                },
                "payment_terms": "",
                "payment_method": "",
                "bank_account": "",
                "notes": ""
            },
            "receipt": {
                "document_type": "receipt",
                "document_number": "",
                "date": "",
                "seller": {
                    "name": "",
                    "tax_id": ""
                },
                "items": [],
                "totals": {
                    "subtotal": 0.0,
                    "tax_amount": 0.0,
                    "total": 0.0,
                    "currency": "",
                    "payment_method": ""
                }
            },
            "payment": {
                "document_type": "payment",
                "document_number": "",
                "date": "",
                "amount": 0.0,
                "currency": "",
                "payer": {
                    "name": "",
                    "account": ""
                },
                "recipient": {
                    "name": "",
                    "account": ""
                },
                "reference": "",
                "payment_method": "",
                "notes": ""
            }
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
        # Simple implementation - can be enhanced with more sophisticated detection
        if any(word in text.lower() for word in ["faktura", "nip", "sprzedawca"]):
            return "pl"
        return "en"
        
    def _load_extraction_patterns(self) -> Dict[str, Any]:
        """
        Load extraction patterns for different languages and fields.
        
        Returns:
            Dictionary of patterns organized by language and field
        """
        return {
            "en": {
                "document_number": [
                    r"(?:invoice|bill|receipt)[^\n\d]*([A-Z0-9-]+)",
                    r"(?:no\.?|nr|#)\s*([A-Z0-9-]+)"
                ],
                "dates": {
                    "issue_date": [
                        r"(?:date|issue date|invoice date)[^\n:]*[:\s]+([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})",
                        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*(?=invoice|date|issue)"
                    ],
                    "due_date": [
                        r"(?:due date|payment due|pay by)[^\n:]*[:\s]+([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})",
                        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*(?=due|payment|pay by)"
                    ]
                },
                "parties": {
                    "seller": [
                        r"(?:from|seller|provider|supplier)[^\n:]*[:\s]+([^\n]+)",
                        r"(?:sprzedawca|wystawca)[^\n:]*[:\s]+([^\n]+)"
                    ],
                    "buyer": [
                        r"(?:to|buyer|customer|recipient)[^\n:]*[:\s]+([^\n]+)",
                        r"(?:nabywca|odbiorca)[^\n:]*[:\s]+([^\n]+)"
                    ]
                },
                "items": {
                    "line_item": [
                        r"(\d+)\s+(.+?)\s+(\d+[\.]?\d*)\s+([0-9\s,]+[\.]\d{2})\s+([0-9\s,]+[\.]\d{2})",
                        r"(.+?)\s+(\d+[\.]?\d*)\s+([0-9\s,]+[\.]\d{2})\s+([0-9\s,]+[\.]\d{2})"
                    ]
                },
                "totals": {
                    "subtotal": [
                        r"subtotal[^\d]*([0-9\s,]+[\.]\d{2})",
                        r"net[^\d]*([0-9\s,]+[\.]\d{2})"
                    ],
                    "tax_amount": [
                        r"(?:vat|tax)[^\d]*([0-9\s,]+[\.]\d{2})",
                        r"tax[^\d]*([0-9\s,]+[\.]\d{2})"
                    ],
                    "total": [
                        r"(?:total|amount due|total due|to pay)[^\d]*([0-9\s,]+[\.]\d{2})",
                        r"(?:total|amount)[^\d]*([0-9\s,]+[\.]\d{2})"
                    ],
                    "currency": [
                        r"([$€£]|USD|EUR|GBP|PLN|JPY|CHF)",
                        r"(?:currency|curr\.?)[^\n:]*[:\s]*([A-Z]{3})"
                    ]
                },
                "payment_terms": [
                    r"(?:payment terms|terms)[^\n:]*[:\s]+([^\n]+)",
                    r"(?:terms of payment)[^\n:]*[:\s]+([^\n]+)"
                ],
                "payment": {
                    "bank_account": [
                        r"(?:bank account|account number|acc\.? no\.?)[^\n:]*[:\s]+([A-Z0-9 ]+)",
                        r"(?:IBAN|account)[^\n:]*[:\s]+([A-Z0-9 ]+)"
                    ],
                    "payment_method": [
                        r"(?:payment method|paid by|via)[^\n:]*[:\s]+([^\n]+)",
                        r"(?:paid via|payment via)[^\n:]*[:\s]+([^\n]+)"
                    ]
                }
            },
            "pl": {
                "document_number": [
                    r"(?:faktura|rachunek|fv)[^\n\d]*(FV[\s\-]?[A-Z0-9\-]+)",
                    r"(?:nr|numer)[^\n:]*[:\s]+([A-Z0-9\-]+)"
                ],
                "dates": {
                    "issue_date": [
                        r"data wystawienia[^\n:]*[:\s]+([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})",
                        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*(?=data wystawienia)"
                    ],
                    "sale_date": [
                        r"data sprzedaży[^\n:]*[:\s]+([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})",
                        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*(?=data sprzedaży)"
                    ],
                    "due_date": [
                        r"termin płatności[^\n:]*[:\s]+([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})",
                        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*(?=termin płatności)"
                    ]
                },
                "parties": {
                    "seller": [
                        r"sprzedawca[^\n:]*[:\s]+([^\n]+)",
                        r"sprzedawca[\s\S]+?nazwa[^\n:]*[:\s]+([^\n]+)"
                    ],
                    "buyer": [
                        r"nabywca[^\n:]*[:\s]+([^\n]+)",
                        r"nabywca[\s\S]+?nazwa[^\n:]*[:\s]+([^\n]+)"
                    ]
                },
                "items": {
                    "line_item": [
                        r"(\d+)\s+(.+?)\s+(\d+[\.,]?\d*)\s+[A-Za-z]*\s*([0-9\s,]+[\.,]\d{2})\s+[A-Za-z]*\s*([0-9\s,]+[\.,]\d{2})",
                        r"(.+?)\s+(\d+[\.,]?\d*)\s+[A-Za-z]*\s*([0-9\s,]+[\.,]\d{2})\s+[A-Za-z]*\s*([0-9\s,]+[\.,]\d{2})"
                    ]
                },
                "totals": {
                    "subtotal": [
                        r"wartość netto[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"netto[^\d]*([0-9\s,]+[\.,]\d{2})"
                    ],
                    "tax_amount": [
                        r"kwota vat[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"podatek[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"vat[^\d]*([0-9\s,]+[\.,]\d{2})"
                    ],
                    "total": [
                        r"wartość brutto[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"razem brutto[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"do zapłaty[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"razem[^\d]*([0-9\s,]+[\.,]\d{2})"
                    ],
                    "currency": [
                        r"([$€£]|PLN|EUR|USD|GBP|CHF)",
                        r"(?:waluta|curr\.?)[^\n:]*[:\s]*([A-Z]{3})"
                    ]
                },
                "payment_terms": [
                    r"forma płatności[^\n:]*[:\s]+([^\n]+)",
                    r"termin płatności[^\n:]*[:\s]+([^\n]+)",
                    r"płatność[^\n:]*[:\s]+([^\n]+)"
                ],
                "payment": {
                    "bank_account": [
                        r"numer konta[^\n:]*[:\s]+([A-Z0-9 ]+)",
                        r"nr rachunku[^\n:]*[:\s]+([A-Z0-9 ]+)",
                        r"IBAN[^\n:]*[:\s]+([A-Z0-9 ]+)"
                    ],
                    "payment_method": [
                        r"forma płatności[^\n:]*[:\s]+([^\n]+)",
                        r"zapłacono[^\n:]*[:\s]+([^\n]+)",
                        r"(przelewem|gotówką|kartą|przelew|przelewem bankowym)"
                    ]
                }
            },
            "de": {
                # Placeholder for German patterns - to be implemented
                "document_number": [
                    r"(?:rechnung|rnr\.?|rechnungsnummer)[^\n:]*[:\s]*([A-Z0-9\-]+)",
                    r"(?:rechnung|rnr\.?|nr\.?)[^\n\d]*(\d+)"
                ],
                "dates": {
                    "issue_date": [
                        r"rechnungsdatum[^\n:]*[:\s]+(\d{1,2}[\./]\d{1,2}[\./]\d{2,4})",
                        r"datum[^\n:]*[:\s]+(\d{1,2}[\./]\d{1,2}[\./]\d{2,4})",
                        r"(\d{1,2}[\./]\d{1,2}[\./]\d{2,4})\s*(?=rechnung|datum|rnr)"
                    ],
                    "due_date": [
                        r"fällig(?:keit)?[^\n:]*[:\s]+(\d{1,2}[\./]\d{1,2}[\./]\d{2,4})",
                        r"zahlbar bis[^\n:]*[:\s]+(\d{1,2}[\./]\d{1,2}[\./]\d{2,4})",
                        r"(\d{1,2}[\./]\d{1,2}[\./]\d{2,4})\s*(?=fällig|zahlbar)"
                    ]
                },
                "totals": {
                    "subtotal": [
                        r"netto[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"zwischensumme[^\d]*([0-9\s,]+[\.,]\d{2})"
                    ],
                    "tax_amount": [
                        r"mwst[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"ust[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"mehrwertsteuer[^\d]*([0-9\s,]+[\.,]\d{2})"
                    ],
                    "total": [
                        r"gesamt[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"endbetrag[^\d]*([0-9\s,]+[\.,]\d{2})",
                        r"rechnungsbetrag[^\d]*([0-9\s,]+[\.,]\d{2})"
                    ],
                    "currency": [
                        r"([$€£]|EUR|CHF|USD|GBP)",
                        r"(?:währung|waehrung|waehr\.?)[^\n:]*[:\s]*([A-Z]{3})"
                    ]
                }
            }
        }
    
    def _parse_date(self, date_str: str) -> str:
        """
        Parse date string into ISO format (YYYY-MM-DD).
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Date string in ISO format (YYYY-MM-DD)
        """
        try:
            # Clean up the date string
            date_str = date_str.strip()
            
            # Try different date formats
            for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", 
                       "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            
            # If no format matched, return the original string
            return date_str
            
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {str(e)}")
            return date_str
    
    def _extract_basic_info(self, text: str, language: str) -> Dict[str, str]:
        """
        Extract basic document information.
        
        Args:
            text: Document text
            language: Language code (e.g., 'en', 'pl')
            
        Returns:
            Dictionary with basic document information
        """
        info = {}
        
        # Extract document number
        doc_number_patterns = self.patterns.get(language, {}).get("document_number", [])
        for pattern in doc_number_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                info["document_number"] = match.group(1).strip()
                break
                
        # Extract dates
        date_patterns = self.patterns.get(language, {}).get("dates", {})
        for date_field, patterns in date_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    info[date_field] = self._parse_date(match.group(1))
                    break
                    
        return info
        
    def _extract_parties(self, text: str, language: str) -> Dict[str, Dict]:
        """Extract seller and buyer information"""
        result = {"seller": {}, "buyer": {}}
        party_patterns = self.patterns.get(language, {}).get("parties", {})
        
        for party_type in ["seller", "buyer"]:
            patterns = party_patterns.get(party_type, [])
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    result[party_type]["name"] = match.group(1).strip()
                    break
                    
        return result
        
    def _extract_items(self, text: str) -> List[Dict]:
        """Extract line items from text"""
        items = []
        patterns = self.patterns.get("en", {}).get("items", {}).get("line_item", [])
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                try:
                    item = {
                        "description": match.group(1).strip(),
                        "quantity": float(match.group(2).replace(",", ".")),
                        "unit_price": float(match.group(3).replace(",", "").replace(" ", "")),
                        "total": float(match.group(4).replace(",", "").replace(" ", ""))
                    }
                    items.append(item)
                except (IndexError, ValueError):
                    continue
                    
        return items
        
    def _extract_totals(self, text: str) -> Dict[str, float]:
        """Extract financial totals"""
        totals = {"subtotal": 0.0, "tax_amount": 0.0, "total": 0.0, "currency": ""}
        patterns = self.patterns.get("en", {}).get("totals", {})
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        # Extract the amount value
                        amount_str = match.group(1).replace(" ", "").replace(",", ".")
                        totals[field] = float(amount_str)
                    except (IndexError, ValueError, AttributeError):
                        continue
                    break
                        
        return totals
        
    def _calculate_confidence(self, data: Dict, text: str) -> float:
        """Calculate confidence score for the extracted data"""
        score = 0
        max_score = 5  # Total possible score
        
        if data.get("document_number"):
            score += 1
        if data.get("issue_date"):
            score += 1
        if data.get("totals", {}).get("total", 0) > 0:
            score += 1
        if data.get("seller", {}).get("name"):
            score += 1
        if data.get("buyer", {}).get("name"):
            score += 1
            
        return min(score / max_score, 1.0)
        
    def _parse_date(self, date_str: str) -> str:
        """Parse date string into ISO format"""
        try:
            # Try common date formats
            for fmt in ["%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return date_str.strip()
        except (ValueError, AttributeError):
            return date_str.strip()

    def _load_extraction_patterns(self) -> Dict[str, Dict]:
        """Load and return extraction patterns for different document fields"""
        return {
            "en": {
                "document_number": [
                    r"(?:Invoice|INVOICE|Bill|BILL)[\s:]*[#]?[\s]*(\S+)",
                    r"(?:No\.?|Number|Nr\.?|#)[\s:]*([A-Z0-9\-\/]+)",
                    r"F[0-9]{4,}-[0-9]+"
                ],
                "dates": {
                    "issue_date": [
                        r"(?:Date|Invoice Date|Issued|Date of Issue)[\s:]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
                        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*(?=Invoice|Date|$)"
                    ],
                    "due_date": [
                        r"(?:Due Date|Due|Payment Due|Due On)[\s:]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
                        r"(?:Payment Terms|Terms)[\s:]+(?:Net|NET)\s*(\d+)\s*(?:days|Days|day|Day)"
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
                "items": {
                    "line_item": [
                        r"(\d+)\s+(.+?)\s+([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})\s+([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})",
                        r"(.+?)\s+([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})\s+([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})"
                    ]
                },
                "totals": {
                    "total": [
                        r"(?:Total|TOTAL|Amount Due|Total Amount)[\s:]*[A-Z]*\s*([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})\s*(?:USD|EUR|GBP|PLN)?"
                    ],
                    "subtotal": [
                        r"(?:Subtotal|Sub-total)[\s:]*[A-Z]*\s*([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})",
                        r"(?:Net|Net Amount)[\s:]*[A-Z]*\s*([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})"
                    ],
                    "tax_amount": [
                        r"(?:Tax|VAT|TAX)[\s:]*[A-Z]*\s*([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})",
                        r"(?:VAT|TAX)[\s(]+\d+%[\s)]*[A-Z]*\s*([$€£]?\s*[0-9,]+\s*[\\.\,]?\d{0,2})"
                    ]
                }
            },
            "pl": {
                "document_number": [
                    r"(?:Faktura|FV|F)[\s:]*[\s]*(\S+)",
                    r"(?:Nr\.?|Numer)[\s:]*([A-Z0-9\-\/]+)",
                    r"FV[\s]*(\d+/\d+)"
                ],
                "dates": {
                    "issue_date": [
                        r"(?:Data wystawienia|Data sprzedaży|Data)[\s:]+(\d{1,2}[\-\.]\d{1,2}[\-\.]\d{2,4})",
                        r"(\d{1,2}[\-\.]\d{1,2}[\-\.]\d{2,4})\s*(?=Faktura|Data|$)"
                    ],
                    "due_date": [
                        r"(?:Termin płatności|Do zapłaty do|Termin)[\s:]+(\d{1,2}[\-\.]\d{1,2}[\-\.]\d{2,4})",
                        r"(?:Termin płatności|Do zapłaty)[\s:]+(\d+)\s*dn[i]?"
                    ]
                },
                "parties": {
                    "seller": [
                        r"(?:Sprzedawca|Wystawca|Fakturujący)[\s:]+(.+?)(?=\s*(?:Nabywca|Kupujący|$))"
                    ],
                    "buyer": [
                        r"(?:Nabywca|Kupujący)[\s:]+(.+?)(?=\s*(?:Sprzedawca|Wystawca|$))"
                    ]
                },
                "items": {
                    "line_item": [
                        r"(\d+)\s+(.+?)\s+(\d+[,\.]?\d*)\s+([0-9\s,]+[,\.]\d{2})\s+([0-9\s,]+[,\.]\d{2})",
                        r"(.+?)\s+(\d+[,\.]?\d*)\s+([0-9\s,]+[,\.]\d{2})\s+([0-9\s,]+[,\.]\d{2})"
                    ]
                },
                "totals": {
                    "total": [
                        r"(?:Razem|Do zapłaty|Suma)[\s:]*[\s]*([0-9\s,]+[,\.]\d{2})\s*(?:zł|PLN)?"
                    ],
                    "subtotal": [
                        r"(?:Wartość netto|Netto|Suma netto)[\s:]*[\s]*([0-9\s,]+[,\.]\d{2})",
                        r"(?:Razem netto|Netto)[\s:]*[\s]*([0-9\s,]+[,\.]\d{2})"
                    ],
                    "tax_amount": [
                        r"(?:VAT|Podatek VAT|Kwota VAT)[\s:]*[\s]*([0-9\s,]+[,\.]\d{2})",
                        r"(?:VAT|Podatek)[\s:]+\d+%[\s:]*[\s]*([0-9\s,]+[,\.]\d{2})"
                    ]
                }
            }
        }
        
        return data

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
        patterns = self.patterns[language]
        
        # Extract seller and buyer sections
        for party_type in ["seller", "buyer"]:
            for pattern in patterns.get("parties", {}).get(party_type, []):
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    party_text = match.group(1).strip()
                    # Extract name (first line)
                    name = party_text.split('\n')[0].strip()
                    parties[party_type]["name"] = name
                    
                    # Extract address (remaining lines)
                    address_lines = [line.strip() for line in party_text.split('\n')[1:] if line.strip()]
                    parties[party_type]["address"] = " ".join(address_lines)
                    break
        
        # Extract contact info
        for party_type in ["seller", "buyer"]:
            if party_type in parties:
                # Extract email
                if "email" not in parties[party_type]:
                    email_matches = re.findall(
                        patterns["contact"]["email"][0], 
                        text, 
                        re.IGNORECASE
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
            
        # Calculate final score (normalized to 0.0-1.0)
        return min(score / max_score, 1.0)

    def _load_extraction_patterns(self) -> Dict[str, Dict]:
                    r"(?:Razem|Do zapłaty|Suma)\s*:?\s*([0-9\s,]+[,\.]\d{2})\s*(?:zł|PLN)?"
                ],
                "subtotal": [r"(?:Netto|Suma netto)\s*:?\s*([0-9\s,]+[,\.]\d{2})"],
                "tax_amount": [r"(?:VAT|Podatek)\s*:?\s*([0-9\s,]+[,\.]\d{2})"],
            },
            "items": {
                "line_item": [
                    r"(\d+)\s+(.+?)\s+(\d+[,\.]?\d*)\s+([0-9\s,]+[,\.]\d{2})\s+([0-9\s,]+[,\.]\d{2})",
                    r"(.+?)\s+(\d+[,\.]?\d*)\s+([0-9\s,]+[,\.]\d{2})\s+([0-9\s,]+[,\.]\d{2})"
                ]
            },
            },
            "parties": {
                "seller": [
                    r"(?:From|Seller|Vendor|Provider)[\s:]+(.+?)(?=\\s*(?:To|Buyer|Client|Customer|$))",
                    r"(?:Bill From|Issuer)[\s:]+(.+?)(?=\\s*(?:Bill To|Recipient|$))"
                ],
                "buyer": [
                    r"(?:To|Bill To|Buyer|Client|Customer)[\s:]+(.+?)(?=\\s*(?:From|Seller|Vendor|$))",
                    r"(?:Ship To|Recipient)[\s:]+(.+?)(?=\\s*(?:From|Issuer|$))"
                ]
            },
            "contact": {
                "email": [r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})"],
                "phone": [r"(?:\\+?\\d{1,3}[-.\\s]?)?\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{3,4}"],
                "tax_id": [r"(?:VAT|TAX|NIP|NIPU|VAT\\s*ID)[\\s:]*([A-Z0-9\\s-]+)", r"\\b[A-Z]{2}[0-9A-Z\\s-]{8,}\\b"]
            },
            "address": {
                "postal_code": [r"\\b[A-Z0-9]{2,4}\\s*[\\-\\s]?\\s*[A-Z0-9]{2,4}\\b"],
                "city": [r"\\b(?:[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)\\s*(?:\\d{2}-?\\d{3})?\\s*[A-Za-z]*"]
            },
        },
        "pl": {
            "basic": {
                "document_number": [
                    r"(?:Faktura|FV|F)\s*[:/]?\\s*([A-Z0-9\\/\\-\\.]+)",
                    r"(?:Nr\\.?|Numer)\s*:?\\s*([A-Z0-9\\/\\-\\.]+)",
                ],
                "document_date": [
                    r"(?:Data faktury|Data wystawienia)[\s:]+(\\d{1,2}[-/]\\d{1,2}[-/]\\d{2,4})",
                    r"Data:\\s*(\\d{1,2}[-/]\\d{1,2}[-/]\\d{2,4})",
                ],
                "due_date": [
                    r"(?:Termin płatności|Do zapłaty do)[\s:]+(\\d{1,2}[-/]\\d{1,2}[-/]\\d{2,4})",
                    r"Termin:\\s*(\\d{1,2}[-/]\\d{1,2}[-/]\\d{2,4})",
                ]
            },
            "contact": {
                "email": [r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})"],
                "phone": [r"(?:\\+?\\d{1,3}[-.\\s]?)?\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{3,4}"],
        },
        "de": {
            # ... German patterns ...
        }
    }


def create_extractor(languages: List[str] = None) -> DataExtractor:
    """Factory function to create data extractor instance"""
    return DataExtractor(languages)
