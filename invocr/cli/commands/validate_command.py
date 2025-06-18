"""
Validate command module.

Handles the 'validate' command for validating extraction results.
"""

import os
import sys
import json
import click
from pathlib import Path

from invocr.utils.logger import get_logger
from ..common import load_yaml_config

logger = get_logger(__name__)


@click.command(name='validate')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-r', '--reference', type=click.Path(exists=True),
              help='Reference file with correct data for comparison')
@click.option('-c', '--config', 'config_file', type=click.Path(exists=True),
              help='Path to YAML configuration file')
@click.option('-o', '--output', 'output_file', type=click.Path(),
              help='Path to save validation report')
@click.option('--ocr', is_flag=True, help='Compare with OCR text for verification')
@click.option('-v', '--verbose', is_flag=True, help='Show detailed validation information')
def validate_command(input_file, reference, config_file, output_file, ocr, verbose):
    """Validate extraction results against reference or OCR"""
    try:
        # Load configuration if provided
        config = None
        if config_file:
            config = load_yaml_config(config_file)
        
        # Load the input file data
        with open(input_file, 'r', encoding='utf-8') as f:
            try:
                input_data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in input file: {e}")
                sys.exit(1)
        
        # Load reference data if provided
        reference_data = None
        if reference:
            with open(reference, 'r', encoding='utf-8') as f:
                try:
                    reference_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in reference file: {e}")
                    sys.exit(1)
        
        # Validate the data
        validation_results = _validate_extraction(input_data, reference_data, ocr)
        
        # Print validation results
        _print_validation_results(validation_results, verbose)
        
        # Save validation report if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(validation_results, f, indent=2)
            logger.info(f"Validation report saved to {output_file}")
        
        # Exit with error if validation failed
        if not validation_results['valid']:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        if verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)


def _validate_extraction(data, reference=None, use_ocr=False):
    """
    Validate extraction against reference data or using OCR verification.
    
    Args:
        data: Extracted data to validate
        reference: Reference data for comparison
        use_ocr: Whether to use OCR for verification
        
    Returns:
        Dictionary with validation results
    """
    results = {
        'valid': True,
        'fields_checked': 0,
        'fields_valid': 0,
        'fields_invalid': 0,
        'details': []
    }
    
    # If no reference and no OCR, just check for required fields
    if not reference and not use_ocr:
        required_fields = ['invoice_number', 'issue_date', 'total_amount']
        for field in required_fields:
            results['fields_checked'] += 1
            if field not in data or not data[field]:
                results['valid'] = False
                results['fields_invalid'] += 1
                results['details'].append({
                    'field': field,
                    'status': 'missing',
                    'message': f"Required field {field} is missing or empty"
                })
            else:
                results['fields_valid'] += 1
                results['details'].append({
                    'field': field,
                    'status': 'valid',
                    'message': f"Field {field} is present"
                })
        
        return results
    
    # Compare with reference data
    if reference:
        for field, ref_value in reference.items():
            results['fields_checked'] += 1
            
            if field not in data:
                results['valid'] = False
                results['fields_invalid'] += 1
                results['details'].append({
                    'field': field,
                    'status': 'missing',
                    'expected': ref_value,
                    'actual': None,
                    'message': f"Field {field} is missing"
                })
                continue
                
            actual_value = data[field]
            if actual_value != ref_value:
                # Special handling for dates, totals, etc. could be added here
                results['valid'] = False
                results['fields_invalid'] += 1
                results['details'].append({
                    'field': field,
                    'status': 'invalid',
                    'expected': ref_value,
                    'actual': actual_value,
                    'message': f"Field {field} does not match expected value"
                })
            else:
                results['fields_valid'] += 1
                results['details'].append({
                    'field': field,
                    'status': 'valid',
                    'expected': ref_value,
                    'actual': actual_value,
                    'message': f"Field {field} matches expected value"
                })
    
    # OCR verification logic would be implemented here
    # This would compare extracted data with OCR text to ensure that
    # values actually appear in the document
    
    return results


def _print_validation_results(results, verbose=False):
    """
    Print validation results to console.
    
    Args:
        results: Validation results dictionary
        verbose: Whether to print detailed results
    """
    if results['valid']:
        logger.info("✓ Validation PASSED")
    else:
        logger.error("✗ Validation FAILED")
        
    logger.info(f"Fields checked: {results['fields_checked']}")
    logger.info(f"Fields valid: {results['fields_valid']}")
    logger.info(f"Fields invalid: {results['fields_invalid']}")
    
    if verbose and results['details']:
        logger.info("\nDetailed validation results:")
        for detail in results['details']:
            if detail['status'] == 'valid':
                logger.info(f"  ✓ {detail['field']}: {detail['message']}")
            else:
                logger.error(f"  ✗ {detail['field']}: {detail['message']}")
                if 'expected' in detail and 'actual' in detail:
                    logger.error(f"    Expected: {detail['expected']}")
                    logger.error(f"    Actual: {detail['actual']}")
