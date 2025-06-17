"""
PDF processing utilities for invoice extraction.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handles PDF processing operations including validation and text extraction."""
    
    def __init__(self, file_path: Optional[str] = None):
        """Initialize PDFProcessor with an optional file path.
        
        Args:
            file_path: Optional path to a PDF file
        """
        self.file_path = file_path
    
    @staticmethod
    def is_valid_pdf(pdf_path: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a PDF file is valid and can be read.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not os.path.exists(pdf_path):
                return False, f"File does not exist: {pdf_path}"
                
            if not pdf_path.lower().endswith('.pdf'):
                return False, f"Not a PDF file: {pdf_path}"
                
            with open(pdf_path, 'rb') as f:
                # Check if file starts with PDF header
                if f.read(4) != b'%PDF':
                    return False, f"Invalid PDF header in: {pdf_path}"
                    
                # Try to read the PDF
                try:
                    reader = PdfReader(f)
                    if len(reader.pages) == 0:
                        return False, f"Empty PDF: {pdf_path}"
                except Exception as e:
                    return False, f"Error reading PDF: {str(e)}"
                    
            return True, None
            
        except Exception as e:
            error_msg = f"Error validating PDF {pdf_path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def extract_text(pdf_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, error_message)
        """
        try:
            with open(pdf_path, 'rb') as f:
                reader = PdfReader(f)
                text = ""
                for i, page in enumerate(reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n--- PAGE {i} ---\n{page_text}"
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {i} of {pdf_path}: {e}")
                
                if not text.strip():
                    return None, "No text content could be extracted from the PDF"
                    
                return text, None
                
        except Exception as e:
            error_msg = f"Error extracting text from {pdf_path}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def process_pdf(pdf_path: str, output_dir: str) -> Tuple[bool, Optional[str]]:
        """
        Process a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save output files
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate PDF
            is_valid, error = PDFProcessor.is_valid_pdf(pdf_path)
            if not is_valid:
                return False, f"Invalid PDF: {error}"
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output path
            output_path = os.path.join(
                output_dir,
                f"{os.path.splitext(os.path.basename(pdf_path))[0]}.json"
            )
            
            # Extract text
            text, error = PDFProcessor.extract_text(pdf_path)
            if error:
                return False, f"Text extraction failed: {error}"
            
            # Here you would typically process the text further or save it
            # For now, we'll just save the raw text
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing {pdf_path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def process_directory(input_dir: str, output_dir: str) -> Dict[str, Any]:
        """
        Process all PDF files in the input directory.
        
        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory to save output files
            
        Returns:
            Dict with processing statistics
        """
        if not os.path.isdir(input_dir):
            error_msg = f"Input directory does not exist: {input_dir}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Process each PDF file
        results = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "errors": []
        }
        
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(root, file)
                    logger.info(f"Processing PDF: {pdf_path}")
                    
                    success, error = PDFProcessor.process_pdf(pdf_path, output_dir)
                    
                    results["processed"] += 1
                    if success:
                        results["succeeded"] += 1
                        logger.info(f"Successfully processed: {pdf_path}")
                    else:
                        results["failed"] += 1
                        error_info = f"Failed to process {pdf_path}: {error}"
                        results["errors"].append(error_info)
                        logger.error(error_info)
        
        logger.info(f"\nProcessing complete!")
        logger.info(f"Successfully processed: {results['succeeded']} files")
        if results['failed'] > 0:
            logger.warning(f"Failed to process: {results['failed']} files")
        
        results["success"] = results["failed"] == 0
        return results
