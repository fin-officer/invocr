# invocr/__init__.py
"""
InvOCR - Invoice OCR and Conversion System
Universal document processing with OCR capabilities
"""

__version__ = "1.0.0"
__author__ = "InvOCR Team"
__email__ = "team@invocr.com"
__description__ = "Invoice OCR and Conversion System"

from .core.converter import create_converter, create_batch_converter
from .core.ocr import create_ocr_engine
from .core.extractor import create_extractor

# Main exports
__all__ = [
    "create_converter",
    "create_batch_converter",
    "create_ocr_engine",
    "create_extractor",
    "__version__"
]

# Package metadata
PACKAGE_INFO = {
    "name": "invocr",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "email": __email__,
    "url": "https://github.com/invocr/invocr",
    "license": "MIT"
}

# ---

# invocr/core/__init__.py
"""
Core processing modules for InvOCR
"""

from .converter import UniversalConverter, BatchConverter, create_converter, create_batch_converter
from .ocr import OCREngine, create_ocr_engine
from .extractor import DataExtractor, create_extractor

__all__ = [
    "UniversalConverter",
    "BatchConverter",
    "OCREngine",
    "DataExtractor",
    "create_converter",
    "create_batch_converter",
    "create_ocr_engine",
    "create_extractor"
]

# ---

# invocr/formats/__init__.py
"""
Format handlers for different file types
"""

from .pdf import PDFProcessor
from .image import ImageProcessor
from .json_handler import JSONHandler
from .xml_handler import XMLHandler
from .html_handler import HTMLHandler

__all__ = [
    "PDFProcessor",
    "ImageProcessor",
    "JSONHandler",
    "XMLHandler",
    "HTMLHandler"
]

# ---

# invocr/api/__init__.py
"""
REST API for InvOCR
"""

from .main import app
from .models import (
    ConversionRequest,
    ConversionResponse,
    BatchConversionRequest,
    BatchConversionResponse,
    ConversionStatus,
    HealthResponse,
    SystemInfo
)

__all__ = [
    "app",
    "ConversionRequest",
    "ConversionResponse",
    "BatchConversionRequest",
    "BatchConversionResponse",
    "ConversionStatus",
    "HealthResponse",
    "SystemInfo"
]

# ---

# invocr/cli/__init__.py
"""
Command Line Interface for InvOCR
"""

from .commands import cli

__all__ = ["cli"]

# ---

# invocr/utils/__init__.py
"""
Utility modules for InvOCR
"""

from .config import get_settings, Settings
from .logger import get_logger, setup_logging
from .helpers import (
    ensure_directory,
    clean_filename,
    get_file_hash,
    format_file_size,
    safe_json_loads
)

__all__ = [
    "get_settings",
    "Settings",
    "get_logger",
    "setup_logging",
    "ensure_directory",
    "clean_filename",
    "get_file_hash",
    "format_file_size",
    "safe_json_loads"
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

__all__ = [
    "TEST_DATA_DIR",
    "TEST_OUTPUT_DIR"
]