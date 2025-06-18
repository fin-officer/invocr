"""
Adapter for invutil package.

This module re-exports functionality from the invutil package
to maintain backward compatibility with existing code.
"""

# Re-export core utilities from invutil
from invutil.config import Settings, get_settings, load_config_from_file, create_default_config, validate_config
from invutil.logger import InvOCRLogger, setup_logging, get_logger
from invutil.helpers import (
    get_file_extension, 
    is_valid_file, 
    ensure_directory_exists, 
    get_output_path,
    read_json_file,
    write_json_file
)
from invutil.date_utils import (
    parse_date, 
    format_date, 
    is_valid_date_format,
    normalize_date
)
from invutil.numeric_utils import (
    extract_numeric_value,
    normalize_amount,
    format_currency,
    validate_amount_range
)

# For backward compatibility
from invutil import *
