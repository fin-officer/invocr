"""
File validation utilities for InvOCR.
"""

import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def is_valid_pdf(pdf_path: str, min_size: int = 100) -> Tuple[bool, Optional[str]]:
    """
    Check if a file is a valid PDF.

    Args:
        pdf_path: Path to the PDF file to validate
        min_size: Minimum file size in bytes (default: 100)

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check if file exists
        if not os.path.exists(pdf_path):
            return False, f"File does not exist: {pdf_path}"

        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size < min_size:
            return False, f"File is too small (min {min_size} bytes): {file_size} bytes"

        # Check PDF header
        with open(pdf_path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                return False, "Invalid PDF header"

        return True, None

    except Exception as e:
        error_msg = f"Error validating PDF {pdf_path}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def is_valid_pdf_simple(pdf_path: str) -> bool:
    """
    Simple PDF validation that only checks the file header.
    
    Args:
        pdf_path: Path to the PDF file to validate
        
    Returns:
        bool: True if the file appears to be a valid PDF, False otherwise
    """
    try:
        with open(pdf_path, 'rb') as f:
            return f.read(4) == b'%PDF'
    except Exception:
        return False
