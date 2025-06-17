"""
File validation and serialization utilities for InvOCR.
"""

import os
import json
import logging
import decimal
from typing import Tuple, Optional, Any, Union
from datetime import date, datetime

logger = logging.getLogger(__name__)


def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Safely serialize data to JSON, handling non-serializable types.
    
    Args:
        data: Data to serialize
        **kwargs: Additional arguments to pass to json.dumps()
        
    Returns:
        JSON string representation of the data
    """
    def default_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, 'tolist'):  # For numpy arrays
            return obj.tolist()
        elif hasattr(obj, 'item') and callable(obj.item):  # For numpy scalar types
            return obj.item()
        return str(obj)
    
    return json.dumps(data, default=default_serializer, **kwargs)


def safe_json_loads(json_str: str, **kwargs) -> Any:
    """
    Safely deserialize JSON string to Python object.
    
    Args:
        json_str: JSON string to deserialize
        **kwargs: Additional arguments to pass to json.loads()
        
    Returns:
        Deserialized Python object
        
    Raises:
        json.JSONDecodeError: If the input is not valid JSON
    """
    if not isinstance(json_str, str):
        raise ValueError("Input must be a string")
    return json.loads(json_str, **kwargs)


def sanitize_input(input_data: Union[str, bytes, dict, list], max_length: int = 10000) -> str:
    """
    Sanitize input data to prevent injection attacks and ensure data consistency.
    
    Args:
        input_data: Input data to sanitize (str, bytes, dict, or list)
        max_length: Maximum allowed length for string input (default: 10000)
        
    Returns:
        Sanitized string
        
    Raises:
        ValueError: If input is too long or contains invalid characters
    """
    if input_data is None:
        return ""
        
    # Convert bytes to string if needed
    if isinstance(input_data, bytes):
        try:
            input_str = input_data.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError("Input contains invalid UTF-8 characters")
    elif isinstance(input_data, (dict, list)):
        # Convert dict or list to JSON string
        input_str = safe_json_dumps(input_data)
    else:
        input_str = str(input_data)
    
    # Check length
    if len(input_str) > max_length:
        raise ValueError(f"Input exceeds maximum allowed length of {max_length} characters")
    
    # Basic XSS prevention - remove or escape potentially dangerous characters
    # This is a basic example - you might need to adjust based on your specific requirements
    sanitized = input_str.replace('<', '&lt;') \
                         .replace('>', '&gt;') \
                         .replace('"', '&quot;') \
                         .replace("'", '&#39;') \
                         .replace('`', '&#96;')
    
    return sanitized


def validate_file_extension(filename: str, allowed_extensions: set) -> Tuple[bool, Optional[str]]:
    """
    Validate that a file has an allowed extension.
    
    Args:
        filename: Name of the file to validate
        allowed_extensions: Set of allowed file extensions (e.g., {'.pdf', '.jpg'})
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "No filename provided"
        
    # Convert to lowercase for case-insensitive comparison
    allowed_extensions = {ext.lower() for ext in allowed_extensions}
    
    # Get file extension
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    if not ext:
        return False, f"No file extension found. Allowed extensions: {', '.join(allowed_extensions)}"
        
    if ext not in allowed_extensions:
        return False, f"File extension '{ext}' is not allowed. Allowed extensions: {', '.join(allowed_extensions)}"
        
    return True, None

def is_valid_pdf(pdf_path: str, min_size: int = 10) -> Tuple[bool, Optional[str]]:
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
