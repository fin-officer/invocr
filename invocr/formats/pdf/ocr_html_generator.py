"""
OCR to HTML generator with page quadrant splitting.

This module provides functionality to convert PDF documents to HTML with OCR text,
splitting each page into quadrants for more targeted analysis.
"""

import os
import re
import base64
import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import tempfile

import cv2
import numpy as np
from pdf2image import convert_from_path, convert_from_bytes
import pytesseract
from PIL import Image

from invocr.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PageQuadrant:
    """Data class representing a quadrant of a page."""
    id: str
    position: str  # "top-left", "top-right", "bottom-left", "bottom-right"
    image: np.ndarray
    text: str = ""
    confidence: float = 0.0
    bounding_boxes: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.bounding_boxes is None:
            self.bounding_boxes = []


class OCRHTMLGenerator:
    """
    Generator for HTML with OCR text split into quadrants.
    
    This class converts PDF documents to HTML, splitting each page into
    quadrants and performing OCR on each quadrant separately.
    """
    
    def __init__(self, tesseract_lang: str = "eng", dpi: int = 300):
        """
        Initialize the OCR HTML generator.
        
        Args:
            tesseract_lang: Language for Tesseract OCR
            dpi: DPI for PDF to image conversion
        """
        self.logger = logger
        self.tesseract_lang = tesseract_lang
        self.dpi = dpi
    
    def convert_pdf_to_html(self, pdf_path: str, output_path: Optional[str] = None) -> str:
        """
        Convert a PDF document to HTML with OCR text split into quadrants.
        
        Args:
            pdf_path: Path to the PDF file
            output_path: Optional path for the output HTML file
            
        Returns:
            Path to the generated HTML file
        """
        self.logger.info(f"Converting PDF to HTML: {pdf_path}")
        
        # Generate output path if not provided
        if not output_path:
            pdf_name = os.path.basename(pdf_path)
            pdf_dir = os.path.dirname(pdf_path)
            output_path = os.path.join(pdf_dir, f"{os.path.splitext(pdf_name)[0]}_ocr.html")
        
        # Convert PDF to images
        images = self._convert_pdf_to_images(pdf_path)
        self.logger.info(f"Converted PDF to {len(images)} images")
        
        # Process each page
        pages_data = []
        for i, img in enumerate(images):
            self.logger.info(f"Processing page {i+1}/{len(images)}")
            page_data = self._process_page(img, i+1)
            pages_data.append(page_data)
        
        # Generate HTML
        html_content = self._generate_html(pages_data)
        
        # Write HTML to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"Generated HTML file: {output_path}")
        return output_path
    
    def _convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert a PDF document to a list of PIL images.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of PIL images
        """
        try:
            return convert_from_path(pdf_path, dpi=self.dpi)
        except Exception as e:
            self.logger.error(f"Error converting PDF to images: {e}")
            raise
    
    def _process_page(self, page_img: Image.Image, page_num: int) -> Dict[str, Any]:
        """
        Process a page image by splitting it into quadrants and performing OCR.
        
        Args:
            page_img: PIL image of the page
            page_num: Page number
            
        Returns:
            Dictionary with page data
        """
        # Convert PIL image to numpy array for OpenCV
        img_np = np.array(page_img)
        
        # Get image dimensions
        height, width = img_np.shape[:2]
        mid_h, mid_w = height // 2, width // 2
        
        # Define quadrants
        quadrants = [
            PageQuadrant(
                id=f"page{page_num}_top_left",
                position="top-left",
                image=img_np[0:mid_h, 0:mid_w]
            ),
            PageQuadrant(
                id=f"page{page_num}_top_right",
                position="top-right",
                image=img_np[0:mid_h, mid_w:width]
            ),
            PageQuadrant(
                id=f"page{page_num}_bottom_left",
                position="bottom-left",
                image=img_np[mid_h:height, 0:mid_w]
            ),
            PageQuadrant(
                id=f"page{page_num}_bottom_right",
                position="bottom-right",
                image=img_np[mid_h:height, mid_w:width]
            )
        ]
        
        # Process each quadrant
        for quadrant in quadrants:
            self._process_quadrant(quadrant)
        
        # Create base64 encoded image for the full page
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=True) as tmp:
            page_img.save(tmp.name)
            with open(tmp.name, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Return page data
        return {
            "page_num": page_num,
            "width": width,
            "height": height,
            "image_data": img_data,
            "quadrants": quadrants
        }
    
    def _process_quadrant(self, quadrant: PageQuadrant) -> None:
        """
        Process a quadrant by performing OCR.
        
        Args:
            quadrant: PageQuadrant object
        """
        # Convert numpy array to PIL Image for Tesseract
        pil_img = Image.fromarray(quadrant.image)
        
        # Perform OCR with confidence data
        ocr_data = pytesseract.image_to_data(
            pil_img, 
            lang=self.tesseract_lang,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract text and confidence
        texts = []
        total_conf = 0
        word_count = 0
        
        for i, word_text in enumerate(ocr_data['text']):
            if word_text.strip():
                conf = int(ocr_data['conf'][i])
                if conf > 0:  # Ignore words with negative confidence
                    texts.append(word_text)
                    total_conf += conf
                    word_count += 1
                    
                    # Add bounding box
                    quadrant.bounding_boxes.append({
                        'text': word_text,
                        'conf': conf,
                        'x': ocr_data['left'][i],
                        'y': ocr_data['top'][i],
                        'w': ocr_data['width'][i],
                        'h': ocr_data['height'][i]
                    })
        
        # Set quadrant text and confidence
        quadrant.text = ' '.join(texts)
        quadrant.confidence = total_conf / max(1, word_count) if word_count > 0 else 0
    
    def _generate_html(self, pages_data: List[Dict[str, Any]]) -> str:
        """
        Generate HTML content from processed pages data.
        
        Args:
            pages_data: List of page data dictionaries
            
        Returns:
            HTML content as a string
        """
        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <title>OCR Document Analysis</title>',
            '    <style>',
            '        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }',
            '        .page { margin-bottom: 30px; border: 1px solid #ccc; padding: 10px; }',
            '        .page-header { background-color: #f0f0f0; padding: 10px; margin-bottom: 10px; }',
            '        .page-image { position: relative; margin-bottom: 20px; }',
            '        .page-image img { width: 100%; border: 1px solid #ddd; }',
            '        .quadrants { display: flex; flex-wrap: wrap; }',
            '        .quadrant { width: 48%; margin-right: 2%; margin-bottom: 20px; border: 1px solid #eee; padding: 10px; }',
            '        .quadrant-header { background-color: #f9f9f9; padding: 5px; margin-bottom: 10px; }',
            '        .quadrant-text { white-space: pre-wrap; font-family: monospace; }',
            '        .confidence-high { color: green; }',
            '        .confidence-medium { color: orange; }',
            '        .confidence-low { color: red; }',
            '        .bounding-box { position: absolute; border: 1px solid rgba(255, 0, 0, 0.5); background-color: rgba(255, 0, 0, 0.1); }',
            '        .toggle-boxes { margin-bottom: 10px; }',
            '    </style>',
            '    <script>',
            '        function toggleBoundingBoxes(pageNum) {',
            '            const boxes = document.querySelectorAll(`.page${pageNum} .bounding-box`);',
            '            boxes.forEach(box => {',
            '                box.style.display = box.style.display === "none" ? "block" : "none";',
            '            });',
            '        }',
            '    </script>',
            '</head>',
            '<body>'
        ]
        
        # Add each page
        for page_data in pages_data:
            page_num = page_data["page_num"]
            
            html_parts.extend([
                f'<div class="page page{page_num}">',
                f'    <div class="page-header">',
                f'        <h2>Page {page_num}</h2>',
                f'        <div class="toggle-boxes">',
                f'            <button onclick="toggleBoundingBoxes({page_num})">Toggle Bounding Boxes</button>',
                f'        </div>',
                f'    </div>',
                f'    <div class="page-image">',
                f'        <img src="data:image/jpeg;base64,{page_data["image_data"]}" alt="Page {page_num}">',
            ])
            
            # Add bounding boxes (initially hidden)
            for quadrant in page_data["quadrants"]:
                for box in quadrant.bounding_boxes:
                    # Adjust coordinates based on quadrant position
                    x, y = box['x'], box['y']
                    if quadrant.position == "top-right":
                        x += page_data["width"] // 2
                    elif quadrant.position == "bottom-left":
                        y += page_data["height"] // 2
                    elif quadrant.position == "bottom-right":
                        x += page_data["width"] // 2
                        y += page_data["height"] // 2
                    
                    html_parts.append(
                        f'        <div class="bounding-box" style="display:none; left:{x}px; top:{y}px; width:{box["w"]}px; height:{box["h"]}px;" title="{box["text"]} (Conf: {box["conf"]})"></div>'
                    )
            
            html_parts.append('    </div>')
            
            # Add quadrants
            html_parts.append('    <div class="quadrants">')
            
            for quadrant in page_data["quadrants"]:
                # Determine confidence class
                conf_class = "confidence-low"
                if quadrant.confidence >= 80:
                    conf_class = "confidence-high"
                elif quadrant.confidence >= 50:
                    conf_class = "confidence-medium"
                
                html_parts.extend([
                    f'        <div class="quadrant" id="{quadrant.id}">',
                    f'            <div class="quadrant-header">',
                    f'                <h3>{quadrant.position.replace("-", " ").title()}</h3>',
                    f'                <p class="{conf_class}">Confidence: {quadrant.confidence:.1f}%</p>',
                    f'            </div>',
                    f'            <div class="quadrant-text">{quadrant.text}</div>',
                    f'        </div>'
                ])
            
            html_parts.extend([
                '    </div>',
                '</div>'
            ])
        
        html_parts.extend([
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)


def pdf_to_html_with_quadrants(pdf_path: str, output_path: Optional[str] = None, 
                              lang: str = "eng", dpi: int = 300) -> str:
    """
    Convert a PDF document to HTML with OCR text split into quadrants.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Optional path for the output HTML file
        lang: Language for Tesseract OCR
        dpi: DPI for PDF to image conversion
        
    Returns:
        Path to the generated HTML file
    """
    generator = OCRHTMLGenerator(tesseract_lang=lang, dpi=dpi)
    return generator.convert_pdf_to_html(pdf_path, output_path)
