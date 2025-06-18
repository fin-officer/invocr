"""
OCR Utility Module

This module provides functions for extracting text from PDF files using various OCR engines
and processing techniques. It includes multi-engine fallback strategies and image preprocessing.
"""

import os
import sys
import subprocess
import tempfile
import logging
import shutil
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Check for available OCR tools
TESSERACT_AVAILABLE = shutil.which('tesseract') is not None
PDFTOTEXT_AVAILABLE = shutil.which('pdftotext') is not None
PDFTOPPM_AVAILABLE = shutil.which('pdftoppm') is not None

def extract_text(file_path: str, languages: Optional[List[str]] = None, 
                 use_layout: bool = True, pages: Optional[List[int]] = None) -> str:
    """
    Extract text from a PDF file using multiple OCR engines with fallback strategy.
    
    Args:
        file_path: Path to the PDF file
        languages: List of language codes for OCR (e.g., ['eng', 'pol', 'deu'])
        use_layout: Whether to preserve layout information
        pages: Specific pages to extract (None for all pages)
        
    Returns:
        Extracted text from the PDF
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return ""
    
    # Try different extraction methods with fallback
    logger.info(f"Extracting text from {file_path}")
    
    # Method 1: Try pdftotext first (fastest and most reliable for text PDFs)
    if PDFTOTEXT_AVAILABLE:
        logger.info("Attempting extraction with pdftotext")
        text = extract_with_pdftotext(file_path, use_layout)
        if text and len(text.strip()) > 100:  # Check if we got meaningful text
            logger.info("Successfully extracted text with pdftotext")
            return text
    
    # Method 2: Try Tesseract OCR
    if TESSERACT_AVAILABLE and PDFTOPPM_AVAILABLE:
        logger.info("Attempting extraction with Tesseract OCR")
        text = extract_with_tesseract(file_path, languages, pages)
        if text:
            logger.info("Successfully extracted text with Tesseract OCR")
            return text
    
    # Method 3: Fallback to basic text extraction
    logger.warning("Falling back to basic text extraction")
    return extract_basic_text(file_path)

def extract_with_pdftotext(file_path: str, use_layout: bool = True) -> str:
    """
    Extract text from PDF using pdftotext command line tool.
    
    Args:
        file_path: Path to the PDF file
        use_layout: Whether to preserve layout information
        
    Returns:
        Extracted text
    """
    try:
        cmd = ['pdftotext']
        if use_layout:
            cmd.append('-layout')
        cmd.extend([file_path, '-'])
        
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"pdftotext error: {e.stderr}")
        return ""
    except Exception as e:
        logger.error(f"Error in pdftotext extraction: {e}")
        return ""

def extract_with_tesseract(file_path: str, languages: Optional[List[str]] = None, 
                          pages: Optional[List[int]] = None) -> str:
    """
    Extract text from PDF using Tesseract OCR after converting to images.
    
    Args:
        file_path: Path to the PDF file
        languages: List of language codes for OCR
        pages: Specific pages to extract
        
    Returns:
        Extracted text
    """
    try:
        # Create temp directory for image files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert PDF to images
            prefix = os.path.join(temp_dir, "page")
            
            # Build pdftoppm command
            cmd = ['pdftoppm', '-png', '-r', '300']
            if pages:
                page_range = ','.join(str(p) for p in pages)
                cmd.extend(['-f', page_range, '-l', page_range])
            cmd.extend([file_path, prefix])
            
            # Run pdftoppm
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Get all generated image files
            image_files = sorted([
                os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                if f.endswith('.png')
            ])
            
            # Process each image with Tesseract
            full_text = []
            for img_file in image_files:
                # Build tesseract command
                cmd = ['tesseract', img_file, 'stdout']
                if languages:
                    lang_str = '+'.join(languages)
                    cmd.extend(['-l', lang_str])
                
                # Run tesseract
                result = subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                full_text.append(result.stdout)
            
            return '\n\n'.join(full_text)
    except subprocess.CalledProcessError as e:
        logger.error(f"OCR error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
        return ""
    except Exception as e:
        logger.error(f"Error in OCR extraction: {e}")
        return ""

def extract_basic_text(file_path: str) -> str:
    """
    Extract basic text from PDF without external dependencies.
    This is a last resort fallback method.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text (may be limited)
    """
    try:
        # Try to read the PDF as text
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # Extract any text strings from binary content
        text_parts = []
        i = 0
        while i < len(content):
            if i + 1 < len(content) and content[i] == ord('(') and content[i+1:i+6].isalnum():
                # Potential text string
                end = content.find(b')', i)
                if end > i:
                    text_part = content[i+1:end].decode('utf-8', errors='ignore')
                    if len(text_part) > 3 and any(c.isalpha() for c in text_part):
                        text_parts.append(text_part)
                    i = end
            i += 1
            
        return '\n'.join(text_parts)
    except Exception as e:
        logger.error(f"Error in basic text extraction: {e}")
        return ""

def extract_text_with_regions(file_path: str, languages: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Extract text from PDF with region-based analysis (top, bottom, left, right).
    
    Args:
        file_path: Path to the PDF file
        languages: List of language codes for OCR
        
    Returns:
        Dictionary with text extracted from different regions
    """
    full_text = extract_text(file_path, languages)
    
    # Split text into lines
    lines = full_text.split('\n')
    total_lines = len(lines)
    
    # Define regions (adjust based on typical invoice layout)
    regions = {
        'top': lines[:total_lines//4],
        'middle': lines[total_lines//4:3*total_lines//4],
        'bottom': lines[3*total_lines//4:],
        'left': [],
        'right': [],
        'full': lines
    }
    
    # Process left/right regions
    for line in lines:
        if not line.strip():
            continue
        
        # Determine if content is more on left or right side
        mid_point = len(line) // 2
        left_content = line[:mid_point].strip()
        right_content = line[mid_point:].strip()
        
        if left_content:
            regions['left'].append(left_content)
        if right_content:
            regions['right'].append(right_content)
    
    # Convert lists back to strings
    return {region: '\n'.join(lines) for region, lines in regions.items()}

def analyze_document_structure(text: str) -> Dict[str, Any]:
    """
    Analyze document structure to identify key sections and layout.
    
    Args:
        text: Extracted text from document
        
    Returns:
        Dictionary with document structure analysis
    """
    lines = text.split('\n')
    structure = {
        'total_lines': len(lines),
        'empty_lines': sum(1 for line in lines if not line.strip()),
        'sections': [],
        'potential_headers': [],
        'potential_tables': [],
        'potential_totals': []
    }
    
    # Identify potential headers (short lines at the beginning)
    header_section = []
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        if line.strip() and len(line) < 50:
            header_section.append((i, line))
            structure['potential_headers'].append((i, line))
    
    # Identify potential tables (lines with consistent spacing/delimiters)
    consecutive_table_lines = 0
    table_start = -1
    
    for i, line in enumerate(lines):
        # Check for table indicators: multiple spaces, tabs, or consistent delimiters
        if ('  ' in line or '\t' in line or line.count('|') > 1 or 
            line.count(':') > 1 or line.count(',') > 2):
            if consecutive_table_lines == 0:
                table_start = i
            consecutive_table_lines += 1
        else:
            if consecutive_table_lines > 2:  # At least 3 lines to consider it a table
                structure['potential_tables'].append({
                    'start': table_start,
                    'end': i - 1,
                    'lines': lines[table_start:i]
                })
            consecutive_table_lines = 0
    
    # Don't forget the last table if it extends to the end
    if consecutive_table_lines > 2:
        structure['potential_tables'].append({
            'start': table_start,
            'end': len(lines) - 1,
            'lines': lines[table_start:]
        })
    
    # Identify potential totals section (near the end, contains amount indicators)
    for i, line in enumerate(lines[-15:]):  # Check last 15 lines
        lower_line = line.lower()
        if any(term in lower_line for term in ['total', 'sum', 'amount', 'subtotal', 'tax', 
                                              'vat', 'net', 'gross', 'razem', 'suma', 'kwota']):
            structure['potential_totals'].append((len(lines) - 15 + i, line))
    
    return structure

def get_document_language_confidence(text: str) -> Dict[str, float]:
    """
    Analyze text to determine likely language and confidence scores.
    
    Args:
        text: Extracted text from document
        
    Returns:
        Dictionary mapping language codes to confidence scores
    """
    # Simple language detection based on common words
    language_markers = {
        'en': ['invoice', 'total', 'payment', 'date', 'amount', 'tax', 'number', 'description', 'quantity', 'price'],
        'pl': ['faktura', 'razem', 'płatność', 'data', 'kwota', 'podatek', 'numer', 'opis', 'ilość', 'cena'],
        'de': ['rechnung', 'gesamt', 'zahlung', 'datum', 'betrag', 'steuer', 'nummer', 'beschreibung', 'menge', 'preis'],
        'es': ['factura', 'total', 'pago', 'fecha', 'importe', 'impuesto', 'número', 'descripción', 'cantidad', 'precio'],
        'fr': ['facture', 'total', 'paiement', 'date', 'montant', 'taxe', 'numéro', 'description', 'quantité', 'prix'],
        'it': ['fattura', 'totale', 'pagamento', 'data', 'importo', 'tassa', 'numero', 'descrizione', 'quantità', 'prezzo'],
        'et': ['arve', 'kokku', 'makse', 'kuupäev', 'summa', 'maks', 'number', 'kirjeldus', 'kogus', 'hind']
    }
    
    text_lower = text.lower()
    scores = {}
    
    for lang, markers in language_markers.items():
        # Count occurrences of each marker
        count = sum(text_lower.count(marker) for marker in markers)
        # Calculate score as percentage of markers found
        scores[lang] = count / len(markers)
    
    return scores

def extract_html_with_regions(file_path: str, languages: Optional[List[str]] = None) -> str:
    """
    Generate HTML representation of PDF with text regions highlighted.
    
    Args:
        file_path: Path to the PDF file
        languages: List of language codes for OCR
        
    Returns:
        HTML string with extracted text organized by regions
    """
    regions = extract_text_with_regions(file_path, languages)
    structure = analyze_document_structure(regions['full'])
    
    html = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '    <meta charset="UTF-8">',
        '    <title>PDF Analysis</title>',
        '    <style>',
        '        body { font-family: Arial, sans-serif; margin: 20px; }',
        '        .region { margin-bottom: 20px; padding: 10px; border: 1px solid #ccc; }',
        '        .region-title { font-weight: bold; margin-bottom: 10px; }',
        '        .top-region { background-color: #f0f8ff; }',
        '        .middle-region { background-color: #f5f5f5; }',
        '        .bottom-region { background-color: #fff0f5; }',
        '        .left-region { background-color: #f0fff0; }',
        '        .right-region { background-color: #fff8dc; }',
        '        .table { background-color: #e6e6fa; }',
        '        .totals { background-color: #ffe4e1; }',
        '        pre { white-space: pre-wrap; }',
        '    </style>',
        '</head>',
        '<body>',
        '    <h1>PDF Analysis Results</h1>',
        f'    <p>File: {os.path.basename(file_path)}</p>'
    ]
    
    # Add document structure information
    html.append('    <h2>Document Structure</h2>')
    html.append('    <ul>')
    html.append(f'        <li>Total lines: {structure["total_lines"]}</li>')
    html.append(f'        <li>Empty lines: {structure["empty_lines"]}</li>')
    html.append(f'        <li>Potential tables: {len(structure["potential_tables"])}</li>')
    html.append(f'        <li>Potential total sections: {len(structure["potential_totals"])}</li>')
    html.append('    </ul>')
    
    # Add regions
    html.append('    <h2>Text Regions</h2>')
    
    for name, content in regions.items():
        if name == 'full':
            continue  # Skip full content as it's redundant
        
        css_class = f"{name}-region"
        html.append(f'    <div class="region {css_class}">')
        html.append(f'        <div class="region-title">{name.upper()} REGION</div>')
        html.append(f'        <pre>{content}</pre>')
        html.append('    </div>')
    
    # Add tables
    if structure['potential_tables']:
        html.append('    <h2>Detected Tables</h2>')
        for i, table in enumerate(structure['potential_tables']):
            html.append(f'    <div class="region table">')
            html.append(f'        <div class="region-title">TABLE {i+1} (Lines {table["start"]}-{table["end"]})</div>')
            html.append(f'        <pre>{chr(10).join(table["lines"])}</pre>')
            html.append('    </div>')
    
    # Add totals
    if structure['potential_totals']:
        html.append('    <h2>Detected Totals</h2>')
        html.append(f'    <div class="region totals">')
        html.append(f'        <div class="region-title">TOTALS SECTION</div>')
        html.append(f'        <pre>{chr(10).join(line for _, line in structure["potential_totals"])}</pre>')
        html.append('    </div>')
    
    html.append('</body>')
    html.append('</html>')
    
    return '\n'.join(html)
