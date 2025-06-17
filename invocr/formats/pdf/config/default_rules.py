"""
Default extraction rules for common invoice formats.

This module contains predefined patterns and rules for extracting
structured data from various invoice formats.
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import date, datetime

# Common date formats for parsing
DATE_FORMATS = [
    '%Y-%m-%d',   # 2023-10-15
    '%d.%m.%Y',   # 15.10.2023
    '%d/%m/%Y',   # 15/10/2023
    '%d-%m-%Y',   # 15-10-2023
    '%Y/%m/%d',   # 2023/10/15
    '%d %b %Y',   # 15 Oct 2023
    '%d %B %Y',   # 15 October 2023
    '%b %d, %Y',  # Oct 15, 2023
    '%B %d, %Y',  # October 15, 2023
    '%d-%b-%Y',   # 15-Oct-2023
    '%d-%B-%Y',   # 15-October-2023
    '%d.%m.%y',   # 15.10.23
    '%d/%m/%y',   # 15/10/23
    '%d-%m-%y',   # 15-10-23
    '%y-%m-%d',   # 23-10-15 (ISO format with 2-digit year)
]

# Common currency symbols and their ISO codes
CURRENCY_SYMBOLS = {
    '$': 'USD',
    '€': 'EUR',
    '£': 'GBP',
    '¥': 'JPY',
    '₹': 'INR',
    'R$': 'BRL',
    'zł': 'PLN',
    'kr': 'SEK',
    'CHF': 'CHF',
    'A$': 'AUD',
    'C$': 'CAD',
    'HK$': 'HKD',
    'S$': 'SGD',
    '¥': 'CNY',
    '₽': 'RUB',
    '₩': 'KRW',
    '₺': 'TRY',
    'R': 'ZAR',
    'MXN': 'MXN',
    'NOK': 'NOK',
    'DKK': 'DKK',
    'CZK': 'CZK',
    'HUF': 'HUF',
    'RON': 'RON',
    'BGN': 'BGN',
    'HRK': 'HRK'
}

# Default extraction rules for common invoice fields
DEFAULT_RULES: Dict[str, Any] = {
    # Invoice metadata
    'invoice_number': [
        {
            'pattern': r'(?i)(?:invoice|facture|rechnung|fattura|factura|faktura)[\s:]+([A-Z0-9-]+)',
            'type': 'str',
            'case_insensitive': True,
            'confidence': 0.9,
            'description': 'Invoice number after common labels'
        },
        {
            'pattern': r'(?i)(?:no\.?|nr\.?|#)[\s:]*([A-Z0-9-]+)',
            'type': 'str',
            'confidence': 0.8,
            'description': 'Number after No./Nr/#'
        },
        {
            'pattern': r'^\s*(?:INV|FAC|FT|FA)[-\s]?(\d+)\s*$',
            'type': 'str',
            'confidence': 0.85,
            'description': 'Standalone invoice number (e.g., INV-123)'
        }
    ],
    
    'issue_date': [
        {
            'pattern': r'(?i)date\s+paid\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
            'type': 'date',
            'confidence': 0.95,
            'date_formats': ['%B %d, %Y'],
            'priority': 1
        },
        {
            'pattern': r'(?i)(?:date|datum|fecha|data|datum|date de facturation)[\s:]+([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.](?:[0-9]{2}|[0-9]{4}))',
            'type': 'date',
            'confidence': 0.9,
            'date_formats': ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y']
        },
        {
            'pattern': r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            'type': 'date',
            'date_formats': ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%m/%d/%Y', '%m-%d-%Y'],
            'confidence': 0.7,
            'description': 'Generic date format (DD/MM/YYYY or MM/DD/YYYY)'
        },
        {
            'pattern': r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            'type': 'date',
            'date_formats': ['%Y-%m-%d', '%Y/%m/%d'],
            'confidence': 0.8,
            'description': 'ISO date format (YYYY-MM-DD)'
        }
    ],
    
    'due_date': [
        {
            'pattern': r'(?i)(?:due\s*date|payment\s*due|zahlungstermin|date d\'\'échéance|data scadenza|fecha de vencimiento)[\s:]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            'type': 'date',
            'confidence': 0.9,
            'description': 'Due date after common labels'
        },
        {
            'pattern': r'(?i)due\s+(?:on|by)[\s:]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            'type': 'date',
            'confidence': 0.85,
            'description': 'Due on/by date'
        },
        {
            'pattern': r'(?i)net\s+(\d+)\s+(?:days|days|dagen|jours|giorni|días)',
            'type': 'relative_date',
            'confidence': 0.8,
            'description': 'Net days (e.g., Net 30)'
        }
    ],
    
    # Seller information
    'seller.name': [
        {
            'pattern': r'^([A-Za-z0-9][^\n]+?)\s*\n(?:\s*\S+\s+\S+\s+\S+\s*\n)?\s*Bill to',
            'type': 'str',
            'confidence': 0.95,
            'priority': 1
        },
        {
            'pattern': r'(?i)(?:from|seller|vendor|supplier|lieferant|fournisseur|fornecedor)[\s:]+(.+?)(?=\n|$|[A-Z][a-z]+\s*:)',
            'type': 'str',
            'confidence': 0.85,
            'description': 'Seller name after common labels'
        },
        {
            'pattern': r'^\s*([A-Z][A-Za-z0-9\s\.\-&,]+)(?:\n|$)',
            'type': 'str',
            'confidence': 0.7,
            'description': 'Company name at start of line'
        }
    ],
    
    'seller.tax_id': [
        {
            'pattern': r'(?i)(?:vat|mwst|tva|iva|btw|tax id|steuernummer|numéro de tva|partita iva|nif|cif)[\s:]+([A-Z0-9\-\s]+)',
            'type': 'str',
            'confidence': 0.9,
            'description': 'VAT/Tax ID after common labels'
        }
    ],
    
    'seller.address': [
        {
            'pattern': r'(?m)^([A-Za-z0-9][^\n]+?)\s*\n(?:\s*[^\n]+\s*\n)?\s*Bill to',
            'type': 'str',
            'confidence': 0.9,
            'priority': 1,
            'group': 1
        },
        {
            'pattern': r'(?i)(?:seller\s+address|vendor\s+address|company\s+address)[\s:]+(.+?)(?=\n|$|\s+[A-Z][a-z]+\s*:)'
        },
        {
            'pattern': r'\d+\s+[\w\s]+(?:\n|,)\s*[A-Za-z\s]+(?:\n|,)\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?',
            'type': 'str',
            'confidence': 0.8,
            'description': 'US-style address pattern'
        }
        {
            'pattern': r'\d+\s+[\w\s]+(?:\n|,)\s*[A-Za-z\s]+(?:\n|,)\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?',
            'type': 'str',
            'confidence': 0.8,
            'description': 'US-style address pattern'
        }
    ],
    
    'seller.email': [
        {
            'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'type': 'str',
            'confidence': 0.9,
            'description': 'Email address pattern'
        }
    ],
    
    'seller.phone': [
        {
            'pattern': r'(?i)(?:phone|tel|telefon|téléphone|telefono|teléfono)[\s:]+([+\d\s\-\(\)]+)',
            'type': 'str',
            'confidence': 0.85,
            'description': 'Phone number after label'
        }
    ],
    
    # Buyer information (similar patterns to seller)
    'buyer.name': [
        {
            'pattern': r'(?i)(?:to|bill to|customer|buyer|kunde|client|cliente)[\s:]+(.+?)(?:\n|$)',
            'type': 'str',
            'confidence': 0.85,
            'description': 'Buyer name after common labels'
        },
        {
            'pattern': r'(?i)(?:ship to|deliver to|lieferadresse|livraison à|spedire a|enviar a)[\s:]+(.+?)(?:\n|$)',
            'type': 'str',
            'confidence': 0.8,
            'description': 'Shipping address name'
        }
    ],
    
    'buyer.tax_id': [
        {
            'pattern': r'(?i)(?:customer\s+(?:vat|mwst|tva|iva|btw|tax id)|tax\s+id)[\s:]+([A-Z0-9\-\s]+)',
            'type': 'str',
            'confidence': 0.9,
            'description': 'Buyer tax ID'
        }
    ],
    
    # Totals and amounts
    'total_amount': [
        {
            'pattern': r'(?i)total\s+\$?([0-9]+[,\.]?[0-9]*)',
            'type': 'currency',
            'confidence': 0.98,
            'priority': 1
        },
        {
            'pattern': r'(?i)(?:total\s+amount|total|summe|total\s+\u00e0\s+payer|importe\s+total|total\s+general)[\s:]*[$\u20ac\u00a3\u00a5]?\s*([0-9]+[,\.]?[0-9]*)',
            'type': 'currency',
            'confidence': 0.95,
            'description': 'Total amount with optional currency'
        },
        {
            'pattern': r'\bTOTAL\b[^\d]*([0-9]+[,.][0-9]{2})',
            'type': 'decimal',
            'confidence': 0.9,
            'description': 'Standalone total amount'
        }
    ],
    
    'tax_amount': [
        {
            'pattern': r'(?i)(?:vat|mwst|tva|iva|btw|tax)[\s:]+(?:\d+%)?\s*[A-Z]{0,3}\s*[=:]?\s*([0-9]+[,.][0-9]{2})',
            'type': 'decimal',
            'confidence': 0.9,
            'description': 'Tax amount with optional rate'
        }
    ],
    
    'subtotal': [
        {
            'pattern': r'(?i)(?:sub-?total|zwischensumme|sous-total|subtotal|subtotale)[\s:]+(?:[A-Z]{3})?\s*([0-9]+[,.][0-9]{2})',
            'type': 'decimal',
            'confidence': 0.9,
            'description': 'Subtotal amount'
        },
        {
            'pattern': r'(?i)(?:netto|net\.?|nettobetrag|montant ht|importe neto|imponibile)[\s:]+(?:[A-Z]{3})?\s*([0-9]+[,.][0-9]{2})',
            'type': 'decimal',
            'confidence': 0.85,
            'description': 'Net amount (pre-tax)'
        }
    ],
    
    'currency': [
        {
            'pattern': r'(?:[€$£¥₹]|USD|EUR|GBP|JPY|INR|CAD|AUD|CHF|CNY|SEK|NZD|MXN|SGD|HKD|NOK|KRW|TRY|RUB|BRL|ZAR|DKK|PLN|THB|MYR|IDR|HUF|CZK|ILS|CLP|PHP|AED|COP|SAR|QAR|TWD|VND|PEN|RON|HKD|MAD|KWD|BGN|HRK|ISK|UAH|JOD|OMR|TND|BHD|LKR|NPR|PKR|EGP|DZD|MUR|JMD|BBD|BZD|BND|FJD|KYD|GIP|SBD|SLL|SZL|SVC|VUV|WST|XPF|ZMW|ZWL|XAF|XOF|XCD|XPF)',
            'type': 'str',
            'confidence': 0.9,
            'description': 'Currency symbol or code'
        }
    ],
    
    # Line items
    'items': [
        {
            'start_pattern': r'(?i)description\s+Qty\s+Unit price\s+Amount',
            'end_pattern': r'(?i)(?:subtotal|total|summe|total\s+à\s+payer|importe\s+total|total\s+general|total\s+amount)',
            'row_pattern': r'^\s*([^\n\r]+?)\s+([0-9]+(?:[,\.][0-9]+)?)\s+([$€£¥]?\s*[0-9]+(?:[,\.][0-9]+))\s+([$€£¥]?\s*[0-9]+(?:[,\.][0-9]+))\s*$',
            'columns': [
                {'name': 'description', 'type': 'str'},
                {'name': 'quantity', 'type': 'float'},
                {'name': 'unit_price', 'type': 'currency'},
                {'name': 'amount', 'type': 'currency'}
            ],
            'required': ['description', 'quantity', 'unit_price', 'amount'],
            'confidence': 0.9,
            'priority': 1
        },
        {
            'start_pattern': r'(?i)(?:description|item|description|bezeichnung|artikel)[\s\|\-\_]*[\n\r]+(?:[-\s\|\_]+[\n\r]+)?',
            'end_pattern': r'(?i)(?:subtotal|total|summe|total\s+à\s+payer|importe\s+total|total\s+general|total\s+amount)',
            'row_pattern': r'^\s*([^\n\r]+?)\s+([0-9]+(?:[,\.][0-9]+)?)\s+([$€£¥]?\s*[0-9]+(?:[,\.][0-9]+))\s*$',
            'columns': [
                {'name': 'description', 'type': 'str'},
                {'name': 'quantity', 'type': 'float'},
                {'name': 'unit_price', 'type': 'currency'}
            ],
            'required': ['description', 'quantity', 'unit_price'],
            'confidence': 0.8,
            'description': 'Simpler line items with description, quantity, unit price'
        }
    ],
    
    # Payment terms
    'payment_terms': [
        {
            'pattern': r'(?i)(?:payment\s+terms|zahlungsbedingungen|conditions de paiement|termini di pagamento|términos de pago)[\s:]+(.+?)(?=\n|$)',
            'type': 'str',
            'confidence': 0.9,
            'description': 'Payment terms after label'
        },
        {
            'pattern': r'(?i)(?:net|due)\s+(\d+)\s+(?:days|tagen|jours|giorni|d[ií]as)',
            'type': 'relative_days',
            'confidence': 0.85,
            'description': 'Net payment terms (e.g., Net 30)'
        }
    ],
    
    # Additional fields
    'purchase_order': [
        {
            'pattern': r'(?i)(?:purchase\s*order|bestellnummer|bon de commande|ordine d\'\'acquisto|orden de compra)[\s:]+([A-Z0-9-]+)',
            'type': 'str',
            'confidence': 0.9,
            'description': 'Purchase order number'
        }
    ],
    
    'payment_method': [
        {
            'pattern': r'(?i)(?:payment\s+method|zahlungsmethode|moyen de paiement|metodo di pagamento|método de pago)[\s:]+(.+?)(?=\n|$)',
            'type': 'str',
            'confidence': 0.85,
            'description': 'Payment method'
        }
    ]
}

def get_default_rules() -> Dict[str, Any]:
    """Get the default extraction rules.
    
    Returns:
        Dictionary containing all default extraction rules
    """
    return DEFAULT_RULES

def get_currency_symbols() -> Dict[str, str]:
    """Get the mapping of currency symbols to ISO codes.
    
    Returns:
        Dictionary mapping currency symbols to their ISO codes
    """
    return CURRENCY_SYMBOLS

def get_date_formats() -> List[str]:
    """Get the list of supported date formats.
    
    Returns:
        List of date format strings
    """
    return DATE_FORMATS
