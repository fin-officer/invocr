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
            'pattern': r'(?i)invoice\s+number\s+([A-Z0-9-]+)',
            'type': 'str',
            'confidence': 0.95,
            'priority': 1,
            'description': 'Invoice number after "Invoice number" label'
        },
        {
            'pattern': r'(?i)receipt\s+number\s+([A-Z0-9-]+)',
            'type': 'str',
            'confidence': 0.9,
            'priority': 2,
            'description': 'Receipt number after "Receipt number" label'
        },
        {
            'pattern': r'(?i)(?:invoice|facture|rechnung|fattura|factura|faktura)[\s:]+([A-Z0-9-]+)',
            'type': 'str',
            'confidence': 0.9,
            'description': 'Invoice number after common labels'
        }
    ],
    
    'issue_date': [
        {
            'pattern': r'(?i)date\s+paid\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
            'type': 'date',
            'confidence': 0.95,
            'date_formats': ['%B %d, %Y'],
            'priority': 1,
            'description': 'Date paid format (Month DD, YYYY)'
        },
        {
            'pattern': r'(?i)(?:date|datum|fecha|data|date de facturation)[\s:]+([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.](?:[0-9]{2}|[0-9]{4}))',
            'type': 'date',
            'confidence': 0.9,
            'date_formats': ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y'],
            'description': 'Date after common labels'
        },
        {
            'pattern': r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            'type': 'date',
            'confidence': 0.7,
            'date_formats': ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%m/%d/%Y', '%m-%d-%Y'],
            'description': 'Generic date format (DD/MM/YYYY or MM/DD/YYYY)'
        }
    ],
    
    # Seller information
    'seller.name': [
        {
            'pattern': r'^([A-Z][A-Za-z0-9\s\.\-&,]+?)\s*\n(?:\s*[A-Za-z0-9\s\.\-&,]+\s*\n)?\s*Bill to',
            'type': 'str',
            'confidence': 0.95,
            'priority': 1,
            'description': 'Seller name at top of receipt'
        },
        {
            'pattern': r'(?i)(?:from|seller|vendor|supplier|lieferant|fournisseur|fornecedor)[\s:]+(.+?)(?=\n|$|[A-Z][a-z]+\s*:)'
        }
    ],
    
    'seller.address': [
        {
            'pattern': r'^([A-Za-z0-9][^\n]+?)\s*\n(?:[^\n]+\n){1,3}\s*Bill to',
            'type': 'str',
            'confidence': 0.9,
            'priority': 1,
            'description': 'Seller address block before Bill to'
        }
    ],
    
    # Items
    'items': [
        {
            'pattern': r'(?i)([A-Za-z0-9][^\n]+?)\s+([0-9]+(?:[,\.][0-9]*)?)\s+([$€£¥]?\s*[0-9]+(?:[,\.][0-9]+))\s+([$€£¥]?\s*[0-9]+(?:[,\.][0-9]+))',
            'type': 'item',
            'confidence': 0.8,
            'priority': 1,
            'description': 'Item line with description, quantity, unit price and amount'
        },
        {
            'pattern': r'(?i)([A-Za-z0-9][^\n]+?)\s+([0-9]+(?:[,\.][0-9]*)?)\s+x\s+([$€£¥]?\s*[0-9]+(?:[,\.][0-9]+))\s*=\s*([$€£¥]?\s*[0-9]+(?:[,\.][0-9]+))',
            'type': 'item',
            'confidence': 0.8,
            'priority': 2,
            'description': 'Item line with description, quantity x unit price = amount format'
        }
    ],
    
    # Totals
    'total_amount': [
        {
            'pattern': r'(?i)total\s+\$?([0-9]+[,\.]?[0-9]*)',
            'type': 'currency',
            'confidence': 0.98,
            'priority': 1,
            'description': 'Total amount after "Total" label'
        },
        {
            'pattern': r'(?i)(?:total\s+amount|summe|total\s+à\s+payer|importe\s+total|total\s+general)[\s:]*[$€£¥]?\s*([0-9]+[,\.]?[0-9]*)',
            'type': 'currency',
            'confidence': 0.95,
            'description': 'Total amount with optional currency symbol'
        }
    ],
    
    # Payment method
    'payment_method': [
        {
            'pattern': r'(?i)payment\s+method[\s:]+(.+?)(?=\n|$)',
            'type': 'str',
            'confidence': 0.9,
            'description': 'Payment method after label'
        }
    ]
}

def get_default_rules() -> Dict[str, Any]:
    """Get the default extraction rules.
    
    Returns:
        Dictionary containing all default extraction rules nested under a 'fields' key
        to match the RuleBasedExtractor's expected format.
    """
    return {'fields': DEFAULT_RULES}

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
