"""
PDF processing module for InvOCR.

This module provides the PDFProcessor class which handles various PDF processing operations
including text extraction, page analysis, and document structure analysis.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

import fitz  # PyMuPDF

from .document_models import Document, Page, Block, Line, Word, BBox
from .models import Invoice, InvoiceItem, InvoiceTotals
from .extractor import extract_invoice_data
from .converter import (
    pdf_to_images,
    pdf_to_text,
    extract_tables,
    get_page_count
)

import json
from pathlib import Path
from typing import Union, Dict, Any
from ...utils.helpers import ensure_directory

logger = logging.getLogger(__name__)

class PDFProcessor:
    """
    A class to process PDF documents and extract structured data.
    
    This class provides methods to process PDF files, extract text and metadata,
    and convert documents to various formats.
    """
    
    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        """
        Initialize the PDFProcessor with an optional PDF file.
        
        Args:
            file_path: Optional path to the PDF file to process
        """
        self.file_path = Path(file_path) if file_path and isinstance(file_path, str) else file_path
        self.doc: Optional[fitz.Document] = None
        self._page_count: Optional[int] = None
        self._metadata: Optional[Dict[str, Any]] = None
        
        # Open the PDF file if a path was provided
        if self.file_path and self.file_path.exists():
            self.doc = fitz.open(self.file_path)
    
    def get_text(self) -> str:
        """
        Extract all text from the PDF document.
        
        Returns:
            str: Extracted text from all pages
        """
        if not self.doc:
            raise ValueError("No PDF document loaded. Please provide a valid PDF file.")
            
        text_parts = []
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            text_parts.append(page.get_text())
            
        return "\n\n".join(text_parts)
        
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def open(self) -> 'PDFProcessor':
        """
        Open the PDF document for processing.
        
        Returns:
            self: For method chaining
            
        Raises:
            FileNotFoundError: If the PDF file does not exist
            RuntimeError: If there's an error opening the PDF
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.file_path}")
            
        try:
            self.doc = fitz.open(self.file_path)
            self._page_count = len(self.doc)
            return self
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF {self.file_path}: {str(e)}")
            
    def close(self):
        """Close the PDF document and release resources."""
        if self.doc:
            self.doc.close()
            self.doc = None
            self._page_count = None
            self._metadata = None
            
    @property
    def page_count(self) -> int:
        """Get the number of pages in the PDF."""
        if self._page_count is None:
            if self.doc is None:
                self.open()
            self._page_count = len(self.doc) if self.doc else 0
        return self._page_count
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Get the PDF metadata.
        
        Returns:
            Dictionary containing PDF metadata
        """
        if self._metadata is None:
            if self.doc is None:
                self.open()
            self._metadata = self.doc.metadata if self.doc else {}
        return self._metadata
    
    def extract_text(self, page_numbers: Optional[List[int]] = None) -> Dict[int, str]:
        """
        Extract text from the PDF.
        
        Args:
            page_numbers: List of page numbers (0-based) to extract text from.
                         If None, extracts from all pages.
                         
        Returns:
            Dictionary mapping page numbers to extracted text
        """
        if self.doc is None:
            self.open()
            
        if page_numbers is None:
            page_numbers = list(range(self.page_count))
            
        result = {}
        for page_num in page_numbers:
            if 0 <= page_num < self.page_count:
                page = self.doc.load_page(page_num)
                result[page_num] = page.get_text("text")
                
        return result
    
    def extract_invoice_data(self) -> Invoice:
        """
        Extract structured invoice data from the PDF.
        
        Returns:
            Invoice object containing extracted data
            
        Raises:
            RuntimeError: If the PDF cannot be processed
        """
        if self.doc is None:
            self.open()
            
        # Extract text from all pages
        text_content = self.extract_text()
        full_text = "\n\n".join(text_content.values())
        
        # Use the extractor to parse the text into structured data
        return extract_invoice_data(full_text)
    
    def to_images(self, output_dir: Union[str, Path], dpi: int = 300, 
                 format: str = 'png', page_numbers: Optional[List[int]] = None) -> List[str]:
        """
        Convert PDF pages to images.
        
        Args:
            output_dir: Directory to save the output images
            dpi: DPI for the output images
            format: Output image format (e.g., 'png', 'jpg')
            page_numbers: List of page numbers to convert (0-based). 
                         If None, converts all pages.
                         
        Returns:
            List of paths to the generated image files
        """
        return pdf_to_images(
            str(self.file_path),
            output_dir=output_dir,
            dpi=dpi,
            format=format,
            page_numbers=page_numbers
        )
    
    def to_text(self, output_file: Optional[Union[str, Path]] = None) -> str:
        """
        Convert PDF to plain text.
        
        Args:
            output_file: Optional path to save the extracted text.
                        If None, returns the text as a string.
                        
        Returns:
            Extracted text if output_file is None, otherwise empty string
        """
        text = pdf_to_text(str(self.file_path))
        
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            return ""
            
        return text
    
    def extract_tables(self, page_numbers: Optional[List[int]] = None) -> Dict[int, List[List[List[str]]]]:
        """
        Extract tables from the PDF.
        
        Args:
            page_numbers: List of page numbers (0-based) to extract tables from.
                         If None, extracts from all pages.
                         
        Returns:
            Dictionary mapping page numbers to lists of tables (as 2D arrays)
        """
        return extract_tables(
            str(self.file_path),
            page_numbers=page_numbers
        )
    
    def extract_structured_data(self) -> Dict[str, Any]:
        """
        Extract structured data from the PDF.
        
        Returns:
            Dictionary containing extracted data
        """
        data = {
            'text': self.extract_text(),
            'tables': self.extract_tables(),
            'metadata': self.metadata
        }
        return data
    
    def export_to_json(self, output_file: Union[str, Path], indent: int = 2, **kwargs) -> None:
        """
        Export the processed document to a JSON file.
        
        Args:
            output_file: Path to the output JSON file
            indent: Number of spaces for indentation in the output JSON
            **kwargs: Additional arguments to pass to json.dump()
        """
        data = self.extract_structured_data()
        output_file = Path(output_file)
        ensure_directory(output_file.parent)
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=indent, default=str, **kwargs)
