# invocr/__init__.py
"""
InvOCR - Invoice OCR and Conversion System
Universal document processing with OCR capabilities
"""

__version__ = "1.0.0"
__author__ = "Tom Sapletta"
__email__ = "info@softreck.dev"
__description__ = "Invoice OCR and Conversion System"

# Import core functionality
from .core.converter import (
    BatchConverter,
    UniversalConverter,
    create_batch_converter,
    create_converter,
)
from .core.extractor import DataExtractor, create_extractor
from .core.ocr import OCREngine, create_ocr_engine

# Import format handlers
from .formats.html_handler import HTMLHandler
from .formats.image import ImageProcessor
from .formats.json_handler import JSONHandler
from .formats.pdf import PDFProcessor
from .formats.xml_handler import XMLHandler

# Package metadata
PACKAGE_INFO = {
    "name": "invocr",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "email": __email__,
    "url": "https://github.com/fin-officer/invocr",
    "license": "MIT",
}

# Main exports
__all__ = [
    # Core functionality
    "UniversalConverter",
    "BatchConverter",
    "OCREngine",
    "DataExtractor",
    "create_converter",
    "create_batch_converter",
    "create_ocr_engine",
    "create_extractor",
    # Format handlers
    "PDFProcessor",
    "ImageProcessor",
    "JSONHandler",
    "XMLHandler",
    "HTMLHandler",
    # Metadata
    "__version__",
]

# ---

# invocr/utils/__init__.py
"""
Utility modules for InvOCR
"""

from .utils.config import Settings, get_settings
from .utils.helpers import (
    clean_filename,
    ensure_directory,
    format_file_size,
    get_file_extension,
    get_file_hash,
)
from .utils.logger import get_logger, setup_logging

__all__ = [
    "get_settings",
    "Settings",
    "get_logger",
    "setup_logging",
    "ensure_directory",
    "clean_filename",
    "get_file_hash",
    "format_file_size",
    "safe_json_loads",
]

# ---

# tests/__init__.py
"""
Test suite for InvOCR
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_DATA_DIR = Path(__file__).parent / "fixtures"
TEST_OUTPUT_DIR = Path(__file__).parent / "output"

# Ensure test directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

__all__ = ["TEST_DATA_DIR", "TEST_OUTPUT_DIR"]
