"""
PDF conversion utilities
Handles PDF to text/image conversion and JSON export
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pdfplumber
from pdf2image import convert_from_path

from ...utils.helpers import ensure_directory
from ...utils.logger import get_logger

logger = get_logger(__name__)


def pdf_to_text(pdf_path: Union[str, Path]) -> str:
    """
    Extract text directly from PDF with improved layout preservation

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text with preserved layout
    """
    pdf_path = Path(pdf_path)
    text = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if page_text:
                    text += page_text + "\n\n"
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""
        
    return text


def pdf_to_images(
    pdf_path: Union[str, Path],
    output_dir: Union[str, Path],
    format: str = "png",
    dpi: int = 300,
    page_numbers: Optional[List[int]] = None,
) -> List[Path]:
    """
    Convert PDF pages to images

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save the images
        format: Image format (png, jpg, etc.)
        dpi: Image resolution
        page_numbers: Optional list of page numbers (0-based) to convert.
                    If None, converts all pages.

    Returns:
        List of paths to the generated images
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    ensure_directory(output_dir)
    
    try:
        # Convert PDF to images
        if page_numbers is not None:
            # Convert only specified pages
            images = []
            for page_num in page_numbers:
                try:
                    # Convert specific page (1-based index)
                    img = convert_from_path(pdf_path, dpi=dpi, first_page=page_num+1, last_page=page_num+1)
                    if img:
                        images.append(img[0])
                except Exception as e:
                    logger.warning(f"Error converting page {page_num}: {e}")
        else:
            # Convert all pages
            images = convert_from_path(pdf_path, dpi=dpi)
        
        # Save images
        image_paths = []
        for i, image in enumerate(images):
            # If we have specific page numbers, use them in the filename
            page_num = page_numbers[i] + 1 if page_numbers is not None else i + 1
            image_path = output_dir / f"{pdf_path.stem}_page_{page_num}.{format}"
            image.save(str(image_path), format.upper())
            image_paths.append(image_path)
            
        return image_paths
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        return []


def get_page_count(pdf_path: Union[str, Path]) -> int:
    """
    Get number of pages in PDF

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Number of pages
    """
    pdf_path = Path(pdf_path)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception as e:
        logger.error(f"Error getting page count: {e}")
        return 0


def extract_tables(pdf_path: Union[str, Path]) -> List[List[List[str]]]:
    """
    Extract tables from PDF

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of tables, where each table is a list of rows, and each row is a list of cells
    """
    pdf_path = Path(pdf_path)
    tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception as e:
        logger.error(f"Error extracting tables from PDF: {e}")
        
    return tables

