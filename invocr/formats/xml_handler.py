"""
XML Handler for European Invoice Format
Supports EU standard invoice XML structure
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class XMLHandler:
    """XML format handler with EU invoice standard support"""

    def __init__(self):
        self.namespaces = {
            "eu_invoice": {"prefix": "inv", "uri": "urn:eu:invoice:standard:2024"}
        }

    def to_xml(self, data: Dict[str, Any], format_type: str = "eu_invoice") -> str:
        """
        Convert invoice data to XML format

        Args:
            data: Invoice data dictionary
            format_type: XML format type (eu_invoice, ubl, custom)

        Returns:
            XML string
        """
        if format_type == "eu_invoice":
            return self._to_eu_invoice_xml(data)
        elif format_type == "ubl":
            return self._to_ubl_xml(data)
        else:
            return self._to_generic_xml(data)

    def from_xml(self, xml_input: str) -> Dict[str, Any]:
        """
        Parse XML to invoice data

        Args:
            xml_input: XML string or file path

        Returns:
            Invoice data dictionary
        """
        if Path(xml_input).exists():
            with open(xml_input, "r", encoding="utf-8") as f:
                xml_content = f.read()
        else:
            xml_content = xml_input

        try:
            root = ET.fromstring(xml_content)

            # Detect XML format and parse accordingly
            if "invoice" in root.tag.lower():
                return self._from_eu_invoice_xml(root)
            else:
                return self._from_generic_xml(root)

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return {}

    def _to_eu_invoice_xml(self, data: Dict[str, Any]) -> str:
        """Convert to EU standard invoice XML"""

        # Create root element with namespace
        root = ET.Element("Invoice")
        root.set("xmlns", self.namespaces["eu_invoice"]["uri"])
        root.set("version", "2024.1")

        # Document information
        doc_info = ET.SubElement(root, "DocumentInformation")
        ET.SubElement(doc_info, "InvoiceNumber").text = data.get("document_number", "")
        ET.SubElement(doc_info, "IssueDate").text = data.get("document_date", "")
        ET.SubElement(doc_info, "DueDate").text = data.get("due_date", "")
        ET.SubElement(doc_info, "Currency").text = "EUR"
        ET.SubElement(doc_info, "DocumentType").text = "Commercial Invoice"

        # Seller information
        seller_elem = ET.SubElement(root, "SellerParty")
        seller = data.get("seller", {})

        seller_id = ET.SubElement(seller_elem, "PartyIdentification")
        ET.SubElement(seller_id, "ID").text = seller.get("tax_id", "")
        ET.SubElement(seller_id, "SchemeID").text = "VAT"

        seller_name = ET.SubElement(seller_elem, "PartyName")
        ET.SubElement(seller_name, "Name").text = seller.get("name", "")

        seller_address = ET.SubElement(seller_elem, "PostalAddress")
        address_parts = seller.get("address", "").split("\n")
        if address_parts:
            ET.SubElement(seller_address, "StreetName").text = (
                address_parts[0] if len(address_parts) > 0 else ""
            )
            ET.SubElement(seller_address, "CityName").text = (
                address_parts[1] if len(address_parts) > 1 else ""
            )
            ET.SubElement(seller_address, "CountryCode").text = (
                "PL"  # Default to Poland
            )

        seller_contact = ET.SubElement(seller_elem, "Contact")
        ET.SubElement(seller_contact, "Telephone").text = seller.get("phone", "")
        ET.SubElement(seller_contact, "ElectronicMail").text = seller.get("email", "")

        # Buyer information
        buyer_elem = ET.SubElement(root, "BuyerParty")
        buyer = data.get("buyer", {})

        buyer_id = ET.SubElement(buyer_elem, "PartyIdentification")
        ET.SubElement(buyer_id, "ID").text = buyer.get("tax_id", "")
        ET.SubElement(buyer_id, "SchemeID").text = "VAT"

        buyer_name = ET.SubElement(buyer_elem, "PartyName")
        ET.SubElement(buyer_name, "Name").text = buyer.get("name", "")

        buyer_address = ET.SubElement(buyer_elem, "PostalAddress")
        buyer_address_parts = buyer.get("address", "").split("\n")
        if buyer_address_parts:
            ET.SubElement(buyer_address, "StreetName").text = (
                buyer_address_parts[0] if len(buyer_address_parts) > 0 else ""
            )
            ET.SubElement(buyer_address, "CityName").text = (
                buyer_address_parts[1] if len(buyer_address_parts) > 1 else ""
            )
            ET.SubElement(buyer_address, "CountryCode").text = "PL"

        # Invoice lines
        lines_elem = ET.SubElement(root, "InvoiceLines")

        for i, item in enumerate(data.get("items", []), 1):
            line_elem = ET.SubElement(lines_elem, "InvoiceLine")
            ET.SubElement(line_elem, "ID").text = str(i)

            # Quantity
            quantity_elem = ET.SubElement(line_elem, "InvoicedQuantity")
            quantity_elem.text = str(item.get("quantity", 1))
            quantity_elem.set("unitCode", "PCE")  # Pieces

            # Line total
            line_total = ET.SubElement(line_elem, "LineExtensionAmount")
            line_total.text = f"{item.get('total_price', 0):.2f}"
            line_total.set("currencyID", "EUR")

            # Item details
            item_elem = ET.SubElement(line_elem, "Item")
            ET.SubElement(item_elem, "Description").text = item.get("description", "")
            ET.SubElement(item_elem, "Name").text = item.get("description", "")

            # Price
            price_elem = ET.SubElement(line_elem, "Price")
            price_amount = ET.SubElement(price_elem, "PriceAmount")
            price_amount.text = f"{item.get('unit_price', 0):.2f}"
            price_amount.set("currencyID", "EUR")

            # Tax information
            tax_elem = ET.SubElement(line_elem, "TaxTotal")
            tax_amount = ET.SubElement(tax_elem, "TaxAmount")
            tax_amount.text = f"{item.get('total_price', 0) * 0.23:.2f}"  # 23% VAT
            tax_amount.set("currencyID", "EUR")

            tax_subtotal = ET.SubElement(tax_elem, "TaxSubtotal")
            taxable_amount = ET.SubElement(tax_subtotal, "TaxableAmount")
            taxable_amount.text = f"{item.get('total_price', 0):.2f}"
            taxable_amount.set("currencyID", "EUR")

            tax_category = ET.SubElement(tax_subtotal, "TaxCategory")
            ET.SubElement(tax_category, "ID").text = "S"  # Standard rate
            ET.SubElement(tax_category, "Percent").text = "23.00"
            ET.SubElement(tax_category, "TaxScheme").text = "VAT"

        # Tax totals
        tax_total = ET.SubElement(root, "TaxTotal")
        totals = data.get("totals", {})

        total_tax_amount = ET.SubElement(tax_total, "TaxAmount")
        total_tax_amount.text = f"{totals.get('tax_amount', 0):.2f}"
        total_tax_amount.set("currencyID", "EUR")

        tax_subtotal = ET.SubElement(tax_total, "TaxSubtotal")
        taxable_amount = ET.SubElement(tax_subtotal, "TaxableAmount")
        taxable_amount.text = f"{totals.get('subtotal', 0):.2f}"
        taxable_amount.set("currencyID", "EUR")

        # Legal monetary totals
        monetary_total = ET.SubElement(root, "LegalMonetaryTotal")

        line_extension = ET.SubElement(monetary_total, "LineExtensionAmount")
        line_extension.text = f"{totals.get('subtotal', 0):.2f}"
        line_extension.set("currencyID", "EUR")

        tax_exclusive = ET.SubElement(monetary_total, "TaxExclusiveAmount")
        tax_exclusive.text = f"{totals.get('subtotal', 0):.2f}"
        tax_exclusive.set("currencyID", "EUR")

        tax_inclusive = ET.SubElement(monetary_total, "TaxInclusiveAmount")
        tax_inclusive.text = f"{totals.get('total', 0):.2f}"
        tax_inclusive.set("currencyID", "EUR")

        payable_amount = ET.SubElement(monetary_total, "PayableAmount")
        payable_amount.text = f"{totals.get('total', 0):.2f}"
        payable_amount.set("currencyID", "EUR")

        # Payment information
        if data.get("payment_method") or data.get("bank_account"):
            payment_info = ET.SubElement(root, "PaymentMeans")
            ET.SubElement(payment_info, "PaymentMeansCode").text = "31"  # Bank transfer

            if data.get("bank_account"):
                payee_account = ET.SubElement(payment_info, "PayeeFinancialAccount")
                ET.SubElement(payee_account, "ID").text = data.get("bank_account", "")

        # Additional notes
        if data.get("notes"):
            notes_elem = ET.SubElement(root, "Note")
            notes_elem.text = data.get("notes", "")

        # Generate metadata
        metadata = ET.SubElement(root, "Metadata")
        ET.SubElement(metadata, "GeneratedBy").text = "InvOCR v1.0.0"
        ET.SubElement(metadata, "GeneratedAt").text = datetime.now().isoformat()

        # Convert to string with proper formatting
        self._indent_xml(root)
        xml_str = ET.tostring(root, encoding="unicode", method="xml")

        # Add XML declaration
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    def _to_ubl_xml(self, data: Dict[str, Any]) -> str:
        """Convert to UBL (Universal Business Language) format"""
        # Simplified UBL implementation
        root = ET.Element("Invoice")
        root.set("xmlns", "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2")

        # Basic UBL structure
        ET.SubElement(root, "ID").text = data.get("document_number", "")
        ET.SubElement(root, "IssueDate").text = data.get("document_date", "")
        ET.SubElement(root, "InvoiceTypeCode").text = "380"  # Commercial invoice

        # Convert and return
        self._indent_xml(root)
        xml_str = ET.tostring(root, encoding="unicode", method="xml")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    def _to_generic_xml(self, data: Dict[str, Any]) -> str:
        """Convert to generic XML format"""
        root = ET.Element("Invoice")

        def dict_to_xml(parent, data_dict):
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    child = ET.SubElement(parent, key)
                    dict_to_xml(child, value)
                elif isinstance(value, list):
                    for item in value:
                        child = ET.SubElement(
                            parent, key[:-1]
                        )  # Remove 's' from plural
                        if isinstance(item, dict):
                            dict_to_xml(child, item)
                        else:
                            child.text = str(item)
                else:
                    ET.SubElement(parent, key).text = str(value) if value else ""

        dict_to_xml(root, data)

        self._indent_xml(root)
        xml_str = ET.tostring(root, encoding="unicode", method="xml")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    def _from_eu_invoice_xml(self, root: ET.Element) -> Dict[str, Any]:
        """Parse EU invoice XML format"""
        data = {
            "document_number": "",
            "document_date": "",
            "due_date": "",
            "seller": {},
            "buyer": {},
            "items": [],
            "totals": {},
        }

        # Extract document info
        doc_info = root.find("DocumentInformation")
        if doc_info is not None:
            data["document_number"] = self._get_text(doc_info, "InvoiceNumber")
            data["document_date"] = self._get_text(doc_info, "IssueDate")
            data["due_date"] = self._get_text(doc_info, "DueDate")

        # Extract seller info
        seller_elem = root.find("SellerParty")
        if seller_elem is not None:
            data["seller"] = {
                "name": self._get_text(seller_elem, "PartyName/Name"),
                "tax_id": self._get_text(seller_elem, "PartyIdentification/ID"),
                "address": self._extract_address(seller_elem),
                "phone": self._get_text(seller_elem, "Contact/Telephone"),
                "email": self._get_text(seller_elem, "Contact/ElectronicMail"),
            }

        # Extract buyer info
        buyer_elem = root.find("BuyerParty")
        if buyer_elem is not None:
            data["buyer"] = {
                "name": self._get_text(buyer_elem, "PartyName/Name"),
                "tax_id": self._get_text(buyer_elem, "PartyIdentification/ID"),
                "address": self._extract_address(buyer_elem),
                "phone": self._get_text(buyer_elem, "Contact/Telephone"),
                "email": self._get_text(buyer_elem, "Contact/ElectronicMail"),
            }

        # Extract line items
        lines_elem = root.find("InvoiceLines")
        if lines_elem is not None:
            for line in lines_elem.findall("InvoiceLine"):
                item = {
                    "description": self._get_text(line, "Item/Description"),
                    "quantity": float(self._get_text(line, "InvoicedQuantity") or "1"),
                    "unit_price": float(
                        self._get_text(line, "Price/PriceAmount") or "0"
                    ),
                    "total_price": float(
                        self._get_text(line, "LineExtensionAmount") or "0"
                    ),
                }
                data["items"].append(item)

        # Extract totals
        monetary_total = root.find("LegalMonetaryTotal")
        if monetary_total is not None:
            data["totals"] = {
                "subtotal": float(
                    self._get_text(monetary_total, "TaxExclusiveAmount") or "0"
                ),
                "tax_amount": float(self._get_text(root, "TaxTotal/TaxAmount") or "0"),
                "total": float(self._get_text(monetary_total, "PayableAmount") or "0"),
                "tax_rate": 23.0,
            }

        return data

    def _from_generic_xml(self, root: ET.Element) -> Dict[str, Any]:
        """Parse generic XML format"""

        def xml_to_dict(element):
            result = {}
            for child in element:
                if len(child) > 0:
                    # Has children - recursive call
                    if child.tag in result:
                        if not isinstance(result[child.tag], list):
                            result[child.tag] = [result[child.tag]]
                        result[child.tag].append(xml_to_dict(child))
                    else:
                        result[child.tag] = xml_to_dict(child)
                else:
                    # Leaf node
                    result[child.tag] = child.text or ""
            return result

        return xml_to_dict(root)

    def _extract_address(self, party_elem: ET.Element) -> str:
        """Extract address from party element"""
        address_elem = party_elem.find("PostalAddress")
        if address_elem is None:
            return ""

        parts = []
        street = self._get_text(address_elem, "StreetName")
        city = self._get_text(address_elem, "CityName")

        if street:
            parts.append(street)
        if city:
            parts.append(city)

        return "\n".join(parts)

    def _get_text(self, parent: ET.Element, path: str) -> str:
        """Get text from XML element using path"""
        if parent is None:
            return ""

        current = parent
        for part in path.split("/"):
            current = current.find(part)
            if current is None:
                return ""

        return current.text or ""

    def _indent_xml(self, elem: ET.Element, level: int = 0) -> None:
        """Add proper indentation to XML for pretty printing"""
        indent = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent
