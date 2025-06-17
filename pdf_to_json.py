#!/usr/bin/env python3
import os
import sys
import time
import argparse
import json
import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

# Add the parent directory to the Python path to ensure invocr can be imported
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
# Also add the invocr subdirectory to the path
invocr_dir = os.path.join(project_root, 'invocr')
if os.path.isdir(invocr_dir):
    sys.path.insert(0, invocr_dir)

# Suppress invoice2data logging errors
logging.basicConfig(level=logging.ERROR)

# Disable problematic invoice2data logger
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

for name in logging.root.manager.loggerDict:
    if 'invoice2data' in name:
        logger = logging.getLogger(name)
        logger.handlers = [NullHandler()]
        logger.propagate = False

try:
    from invocr.core.converter import UniversalConverter
    from invocr.formats.pdf.rule_based_extractor import RuleBasedExtractor
    from invocr.formats.pdf.models import Invoice
    from invocr.formats.pdf.config import get_default_rules
    from invocr.formats.pdf.processor import PDFProcessor
except ImportError as e:
    print(f"Error: Failed to import required modules: {e}")
    print("Please install the required dependencies with:")
    print("poetry install")
    print("or")
    print("pip install -e .")
    sys.exit(1)

try:
    from invoice2data import extract_data
    from invoice2data.extract.loader import read_templates
    INVOICE2DATA_AVAILABLE = True
except ImportError:
    print("Warning: invoice2data is not installed. Using only invocr for extraction.")
    print("For better results, install invoice2data with:")
    print("poetry add invoice2data")
    INVOICE2DATA_AVAILABLE = False


def extract_with_rule_based_extractor(pdf_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract data from a PDF file using the RuleBasedExtractor.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing the extracted data
    """
    try:
        # Initialize the PDF processor and extract text
        pdf_processor = PDFProcessor(str(pdf_path))
        text = pdf_processor.get_text()
        
        # Initialize the rule-based extractor with default rules
        rules = get_default_rules()
        extractor = RuleBasedExtractor(rules=rules)
        
        # Extract invoice data
        invoice = extractor.extract_invoice(text)
        
        # Convert to dictionary
        if hasattr(invoice, 'to_dict'):
            return invoice.to_dict()
        return {}
    except Exception as e:
        print(f"  Warning: Rule-based extraction failed: {e}")
        return {}
    
# Define a function to check if a PDF is valid
def is_valid_pdf(pdf_path):
    """Check if a PDF file is valid and not corrupted."""
    try:
        # Try to open the file in binary mode
        with open(pdf_path, 'rb') as f:
            # Check if file starts with PDF header
            header = f.read(5)
            if header != b'%PDF-':
                return False
            
            # Check if file has some minimum size
            f.seek(0, os.SEEK_END)
            if f.tell() < 100:  # Arbitrary small size
                return False
                
        return True
    except Exception:
        return False

def merge_json_data(invocr_data, invoice2data_data):
    """
    Merge data extracted from invocr and invoice2data to create a more complete and accurate JSON.
    
    Args:
        invocr_data (dict): Data extracted by invocr
        invoice2data_data (dict): Data extracted by invoice2data
        
    Returns:
        dict: Merged data with preference given to invoice2data for fields it extracts well
    """
    # Start with invocr data as base
    merged_data = invocr_data.copy()
    
    # If invoice2data didn't extract anything, return just invocr data
    if not invoice2data_data:
        return merged_data
    
    # Map invoice2data fields to invocr fields
    field_mapping = {
        'date': 'issue_date',
        'invoice_number': 'document_number',
        'amount': 'totals.total',
        'amount_untaxed': 'totals.subtotal',
        'amount_tax': 'totals.tax_amount',
        'vat': 'totals.tax_amount',  # Alternative field
        'issuer': 'seller.name',
        'partner_name': 'buyer.name',
        'partner_vat': 'buyer.vat',
        'currency': '_metadata.currency',
        'payment_method': 'payment_method',
        'iban': 'bank_account',
        'bic': '_metadata.bic'
    }
    
    # Copy fields from invoice2data to merged data
    for i2d_field, invocr_field in field_mapping.items():
        if i2d_field in invoice2data_data and invoice2data_data[i2d_field]:
            # Handle nested fields (e.g., totals.total)
            if '.' in invocr_field:
                parts = invocr_field.split('.')
                if parts[0] not in merged_data:
                    merged_data[parts[0]] = {}
                if isinstance(merged_data[parts[0]], dict):
                    merged_data[parts[0]][parts[1]] = invoice2data_data[i2d_field]
            else:
                merged_data[invocr_field] = invoice2data_data[i2d_field]
    
    # Add any additional fields from invoice2data that aren't in the mapping
    if '_metadata' not in merged_data:
        merged_data['_metadata'] = {}
    
    for key, value in invoice2data_data.items():
        if key not in [i2d_field for i2d_field, _ in field_mapping.items()]:
            merged_data['_metadata'][f'i2d_{key}'] = value
    
    return merged_data

def convert_pdf_to_json(pdf_dir, output_dir=None, languages=None, overwrite=False, month=None, year=None, use_invoice2data=True, save_alongside=False):
    """
    Convert PDF files to JSON using invocr and optionally invoice2data.
    
    Args:
        pdf_dir (str): Directory containing PDF files
        output_dir (str, optional): Directory to save JSON files. Not used if save_alongside is True.
        languages (list): List of languages to use for extraction
        overwrite (bool): Whether to overwrite existing JSON files
        month (str): Month to filter by (format: MM)
        year (str): Year to filter by (format: YYYY)
        use_invoice2data (bool): Whether to use invoice2data for extraction
        save_alongside (bool): If True, save JSON files alongside PDFs with the same base name
        
    Returns:
        tuple: (success_count, failure_count) - Number of files successfully converted and failed
    """
    pdf_dir = Path(pdf_dir)
    
    # Handle output directory if not saving alongside PDFs
    if not save_alongside and output_dir:
        output_dir = Path(output_dir)
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get list of PDF files
    pdf_files = []
    print(f"DEBUG: Looking for PDF files in {pdf_dir} (exists: {pdf_dir.exists()})")
    
    # Check if pdf_dir is a file
    if pdf_dir.is_file() and pdf_dir.suffix.lower() == '.pdf':
        print(f"DEBUG: pdf_dir is a single PDF file: {pdf_dir}")
        pdf_files.append(pdf_dir)
    else:
        # Walk directory structure
        for root, dirs, files in os.walk(pdf_dir):
            print(f"DEBUG: Scanning directory: {root}, found {len(files)} files")
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_path = Path(root) / file
                    print(f"DEBUG: Found PDF: {pdf_path}")
                    
                    # Filter by month and year if specified
                    if month or year:
                        try:
                            # Get file modification time
                            mtime = os.path.getmtime(pdf_path)
                            file_time = time.localtime(mtime)
                            file_month = time.strftime('%m', file_time)
                            file_year = time.strftime('%Y', file_time)
                            
                            print(f"DEBUG: File {pdf_path} has month={file_month}, year={file_year}")
                            print(f"DEBUG: Filtering with month={month}, year={year}")
                            
                            # Skip if month doesn't match
                            if month and file_month != month:
                                print(f"DEBUG: Skipping {pdf_path} - month {file_month} doesn't match {month}")
                                continue
                            
                            # Skip if year doesn't match
                            if year and file_year != year:
                                print(f"DEBUG: Skipping {pdf_path} - year {file_year} doesn't match {year}")
                                continue
                        except Exception as e:
                            print(f"  Warning: Failed to get modification time for {pdf_path}: {e}")
                    
                    pdf_files.append(pdf_path)
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return 0, 0
        
    print(f"Found {len(pdf_files)} PDF files to process...")
    
    # Initialize invocr converter
    converter = UniversalConverter(languages=languages or ['en'])
    
    # Load invoice2data templates if available
    if INVOICE2DATA_AVAILABLE and use_invoice2data:
        try:
            templates = read_templates()
            if not templates:
                print("  Warning: No invoice2data templates found. Results may be limited.")
        except Exception as e:
            print(f"  Warning: Failed to load invoice2data templates: {e}")
            templates = []
            use_invoice2data = False
    else:
        use_invoice2data = False
    
    # Process PDF files
    success_count = 0
    failure_count = 0
    skipped_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        # Determine JSON output path based on save_alongside flag
        if save_alongside:
            # Save JSON file alongside PDF with the same base name
            json_file = pdf_file.with_suffix('.json')
        else:
            # If input is a single file, use the output directory directly
            if pdf_file.is_file() and pdf_file.suffix.lower() == '.pdf':
                json_file = output_dir / f"{pdf_file.stem}.json"
            else:
                # Save in output directory with relative path preserved
                rel_path = pdf_file.relative_to(pdf_dir)
                json_file = output_dir / rel_path.with_suffix('.json')
            # Create parent directories if they don't exist
            json_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Skip if JSON file already exists and overwrite is False
        if json_file.exists() and not overwrite:
            print(f"  [{i}/{len(pdf_files)}] Skipping {pdf_file} (output already exists)")
            skipped_count += 1
            continue
        
        # Check if PDF is valid
        if not is_valid_pdf(pdf_file):
            print(f"  [{i}/{len(pdf_files)}] Skipping {pdf_file} (invalid or corrupted PDF file)")
            failure_count += 1
            continue
        
        print(f"  [{i}/{len(pdf_files)}] Converting {pdf_file} to {json_file}...")
        
        # Create temporary file for invocr output
        invocr_json_file = json_file.with_name(f"{json_file.stem}_invocr.json")
        
        try:
            # Extract data using RuleBasedExtractor first
            rule_based_data = extract_with_rule_based_extractor(pdf_file)
            
            # Convert PDF to JSON using the original converter as fallback
            invocr_data = None
            try:
                result = converter.convert(pdf_file, invocr_json_file)
                
                # Load invocr JSON data if file exists
                if invocr_json_file.exists():
                    with open(invocr_json_file, 'r') as f:
                        invocr_data = json.load(f)
                        
                # If we have rule-based data, merge it with the invocr data
                if rule_based_data:
                    print("  Successfully extracted data using RuleBasedExtractor")
                    if invocr_data and isinstance(invocr_data, dict):
                        # Merge rule-based data into invocr data
                        invocr_data.update({"rule_based_data": rule_based_data})
                        invocr_data["metadata"] = invocr_data.get("metadata", {})
                        invocr_data["metadata"]["extraction_methods"] = ["rule_based", "invocr"]
                    else:
                        # Use rule-based data as primary if invocr extraction failed
                        invocr_data = rule_based_data
                        invocr_data["metadata"] = {"extraction_methods": ["rule_based"]}
            except Exception as e:
                print(f"  Warning: invocr extraction failed: {e}")
                # Use rule-based data if available, otherwise create empty data
                if rule_based_data:
                    print("  Using rule-based extraction results")
                    invocr_data = rule_based_data
                    invocr_data["metadata"] = {"extraction_methods": ["rule_based"]}
                else:
                    invocr_data = {"document": {}, "metadata": {"extraction_methods": ["failed"]}}
            
            # Extract data using invoice2data if available
            invoice2data_data = None
            if use_invoice2data and INVOICE2DATA_AVAILABLE:
                print(f"  Extracting with invoice2data...")
                try:
                    # Use a temp directory for any temporary files invoice2data might create
                    with tempfile.TemporaryDirectory() as temp_dir:
                        os.environ["TMPDIR"] = temp_dir
                        invoice2data_data = extract_data(str(pdf_file), templates=templates)
                except Exception as e:
                    print(f"  Warning: invoice2data extraction failed: {e}")
            
            # If both extractions failed, skip this file
            if not invocr_data and not invoice2data_data:
                print(f"  Error: Both invocr and invoice2data failed to extract data from {pdf_file}")
                failure_count += 1
                # Clean up temporary files
                if invocr_json_file.exists():
                    os.remove(invocr_json_file)
                continue
            
            # Merge data from both sources
            if invoice2data_data:
                merged_data = merge_json_data(invocr_data, invoice2data_data)
                print(f"  Successfully merged data from invocr and invoice2data")
            else:
                merged_data = invocr_data
                print(f"  Note: invoice2data didn't extract any data, using only invocr results")
            
            # Write merged data to JSON file
            with open(json_file, 'w') as f:
                json.dump(merged_data, f, indent=2)
            
            # Remove temporary invocr JSON file
            if invocr_json_file.exists():
                os.remove(invocr_json_file)
            
            success_count += 1
            print(f"  Success: {os.path.getsize(json_file)} bytes written")
        except Exception as e:
            print(f"  Error: Failed to create {json_file}: {e}")
            failure_count += 1
            
            # Clean up temporary files
            if invocr_json_file.exists():
                os.remove(invocr_json_file)
    
    print("\nConversion complete!")
    print(f"Successfully converted: {success_count} files")
    if skipped_count > 0:
        print(f"Skipped (already exist): {skipped_count} files")
    print(f"Failed to convert: {failure_count} files")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    
    return success_count, failure_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert PDF invoices to JSON using invocr')
    parser.add_argument('--pdf-dir', default='./attachments', help='Directory containing PDF files (default: ./attachments)')
    parser.add_argument('--output-dir', help='Directory to save JSON files (default: ./json)')
    parser.add_argument('--languages', nargs='+', default=['en', 'pl', 'de'], 
                        help='Languages to use for OCR (default: en pl de)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing JSON files')
    parser.add_argument('--month', type=int, help='Month to process (1-12)')
    parser.add_argument('--year', type=int, help='Year to process (e.g., 2024)')
    parser.add_argument('--no-invoice2data', action='store_true', 
                        help='Disable invoice2data extraction (use only invocr)')
    parser.add_argument('--save-alongside', action='store_true',
                        help='Save JSON files alongside PDFs with the same base name')
    
    args = parser.parse_args()
    
    # Set default output directory if not specified
    if not args.output_dir:
        if args.pdf_dir == './attachments':
            args.output_dir = './json'
        else:
            # Use a json directory at the same level as the input directory
            pdf_dir_path = Path(args.pdf_dir)
            args.output_dir = str(pdf_dir_path.parent / 'json')
    
    # Format month and year as strings if provided
    month_str = f"{args.month:02d}" if args.month else None
    year_str = f"{args.year}" if args.year else None
    
    # If month and year are provided, use them to construct the PDF directory
    if args.month and args.year:
        pathname = os.path.dirname(os.path.abspath(__file__))
        pdf_dir = os.path.join(pathname, f'{args.year}.{month_str}', 'attachments')
        output_dir = os.path.join(pathname, f'{args.year}.{month_str}', 'json')
        
        print(f"Processing PDF files from: {pdf_dir}")
        print(f"Saving JSON files to: {output_dir}")
        
        # Convert PDF to JSON with auto-determined directories
        success, failed = convert_pdf_to_json(
            pdf_dir=pdf_dir,
            output_dir=output_dir,
            languages=args.languages,
            overwrite=args.overwrite,
            month=month_str,
            year=year_str,
            use_invoice2data=not args.no_invoice2data,
            save_alongside=args.save_alongside
        )
    else:
        print(f"Processing PDF files from: {args.pdf_dir}")
        print(f"Saving JSON files to: {args.output_dir}")
        
        # Use the provided or default directories
        success, failed = convert_pdf_to_json(
            pdf_dir=args.pdf_dir,
            output_dir=args.output_dir,
            languages=args.languages,
            overwrite=args.overwrite,
            save_alongside=args.save_alongside,
            month=month_str,
            year=year_str,
            use_invoice2data=not args.no_invoice2data
        )
    
    # Set exit code based on success/failure
    if failed > 0 and success == 0:
        sys.exit(1)  # All conversions failed
    else:
        sys.exit(0)  # At least some conversions succeeded
