"""
Universal format converter for invoices and receipts
Handles PDF, Images, JSON, XML, HTML conversions
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..core.extractor import create_extractor
from ..core.ocr import create_ocr_engine
from ..formats.html_handler import HTMLHandler
from ..formats.image import ImageProcessor
from ..formats.json_handler import JSONHandler
from ..formats.pdf import PDFProcessor
from ..formats.xml_handler import XMLHandler
from ..utils.config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class UniversalConverter:
    """Universal converter supporting all format combinations"""

    def __init__(self, languages: List[str] = None):
        self.languages = languages or ["en", "pl", "de", "fr", "es"]
        self.ocr_engine = create_ocr_engine(self.languages)
        self.extractor = create_extractor(self.languages)

        # Initialize format handlers
        self.pdf_processor = PDFProcessor()
        self.image_processor = ImageProcessor()
        self.json_handler = JSONHandler()
        self.xml_handler = XMLHandler()
        self.html_handler = HTMLHandler()

        logger.info("Universal converter initialized")

    def convert(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        source_format: str = "auto",
        target_format: str = "json",
    ) -> Dict[str, any]:
        """
        Convert between any supported formats

        Args:
            input_path: Source file path
            output_path: Destination file path
            source_format: Source format (auto-detect if 'auto')
            target_format: Target format

        Returns:
            Conversion result with metadata
        """
        try:
            # Auto-detect source format
            if source_format == "auto":
                source_format = self._detect_format(input_path)

            logger.info(f"Converting {source_format} → {target_format}")

            # Load source data
            data = self._load_data(input_path, source_format)

            # Convert to target format
            result = self._save_data(data, output_path, target_format)

            return {
                "success": True,
                "source_format": source_format,
                "target_format": target_format,
                "input_path": str(input_path),
                "output_path": str(output_path),
                "metadata": result,
            }

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "source_format": source_format,
                "target_format": target_format,
            }

    def pdf_to_images(
        self,
        pdf_path: Union[str, Path],
        output_dir: Union[str, Path],
        format: str = "png",
        dpi: int = 300,
    ) -> List[str]:
        """Convert PDF to images (PDF → PNG/JPG)"""
        return self.pdf_processor.to_images(pdf_path, output_dir, format, dpi)

    def image_to_json(
        self, image_path: Union[str, Path], document_type: str = "invoice"
    ) -> Dict[str, any]:
        """Convert image to JSON using OCR (IMG → JSON)"""
        # Extract text using OCR
        ocr_result = self.ocr_engine.extract_text(image_path)

        # Extract structured data
        structured_data = self.extractor.extract_invoice_data(
            ocr_result["text"], document_type
        )

        # Add OCR metadata
        structured_data["_metadata"] = {
            "source_type": "image_ocr",
            "ocr_confidence": ocr_result["confidence"],
            "ocr_engine": ocr_result.get("engine_used", "auto"),
            "languages": self.languages,
            "document_type": document_type,
        }

        return structured_data

    def pdf_to_json(
        self,
        pdf_path: Union[str, Path],
        document_type: str = "invoice",
        use_ocr: bool = True,
    ) -> Dict[str, any]:
        """Convert PDF to JSON (PDF → JSON)"""
        # Try direct text extraction first
        try:
            text_data = self.pdf_processor.extract_text(pdf_path)

            if text_data and len(text_data.strip()) > 50:
                # Direct text extraction successful
                structured_data = self.extractor.extract_invoice_data(
                    text_data, document_type
                )
                structured_data["_metadata"] = {
                    "source_type": "pdf_text",
                    "extraction_method": "direct",
                    "document_type": document_type,
                }
            else:
                raise ValueError("Insufficient text extracted")

        except Exception as e:
            if not use_ocr:
                logger.warning(f"Direct PDF extraction failed: {e}")
                return {"error": "PDF text extraction failed", "use_ocr": True}

            # Fallback to OCR
            logger.info("Falling back to OCR extraction")
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PDF to images
                images = self.pdf_processor.to_images(pdf_path, temp_dir)

                # Process first page (or combine multiple pages)
                if images:
                    combined_text = ""
                    total_confidence = 0

                    for img_path in images[:3]:  # Process max 3 pages
                        ocr_result = self.ocr_engine.extract_text(img_path)
                        combined_text += ocr_result["text"] + "\n"
                        total_confidence += ocr_result["confidence"]

                    avg_confidence = total_confidence / len(images[:3])

                    structured_data = self.extractor.extract_invoice_data(
                        combined_text, document_type
                    )
                    structured_data["_metadata"] = {
                        "source_type": "pdf_ocr",
                        "extraction_method": "ocr",
                        "ocr_confidence": avg_confidence,
                        "pages_processed": len(images[:3]),
                        "document_type": document_type,
                    }
                else:
                    raise ValueError("No images extracted from PDF")

        return structured_data

    def json_to_xml(
        self, json_data: Union[Dict, str, Path], xml_format: str = "eu_invoice"
    ) -> str:
        """Convert JSON to XML (JSON → XML)"""
        if isinstance(json_data, (str, Path)):
            with open(json_data, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json_data

        return self.xml_handler.to_xml(data, xml_format)

    def json_to_html(
        self, json_data: Union[Dict, str, Path], template: str = "modern"
    ) -> str:
        """Convert JSON to HTML (JSON → HTML)"""
        if isinstance(json_data, (str, Path)):
            with open(json_data, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json_data

        return self.html_handler.to_html(data, template)

    def html_to_pdf(
        self,
        html_input: Union[str, Path],
        output_path: Union[str, Path],
        options: Dict = None,
    ) -> str:
        """Convert HTML to PDF (HTML → PDF)"""
        return self.html_handler.to_pdf(html_input, output_path, options)

    def _detect_format(self, file_path: Union[str, Path]) -> str:
        """Auto-detect file format based on extension and content"""
        path = Path(file_path)
        extension = path.suffix.lower()

        format_map = {
            ".pdf": "pdf",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".tiff": "image",
            ".bmp": "image",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".htm": "html",
        }

        detected = format_map.get(extension, "unknown")
        logger.info(f"Detected format: {detected} for {file_path}")
        return detected

    def _load_data(self, file_path: Union[str, Path], format: str) -> Dict[str, any]:
        """Load data from file based on format"""
        if format == "pdf":
            return self.pdf_to_json(file_path)
        elif format == "image":
            return self.image_to_json(file_path)
        elif format == "json":
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif format == "xml":
            return self.xml_handler.from_xml(file_path)
        elif format == "html":
            return self.html_handler.from_html(file_path)
        else:
            raise ValueError(f"Unsupported source format: {format}")

    def _save_data(
        self, data: Dict, file_path: Union[str, Path], format: str
    ) -> Dict[str, any]:
        """Save data to file in specified format"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return {"size": path.stat().st_size}

        elif format == "xml":
            xml_content = self.json_to_xml(data)
            with open(path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            return {"size": path.stat().st_size, "format": "eu_invoice"}

        elif format == "html":
            html_content = self.json_to_html(data)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return {"size": path.stat().st_size, "template": "modern"}

        elif format == "pdf":
            # First convert to HTML, then to PDF
            html_content = self.json_to_html(data)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(html_content)
                tmp.flush()
                self.html_to_pdf(tmp.name, path)
            return {"size": path.stat().st_size, "pages": 1}

        else:
            raise ValueError(f"Unsupported target format: {format}")


class BatchConverter:
    """Batch processing for multiple files"""

    def __init__(self, languages: List[str] = None):
        self.converter = UniversalConverter(languages)

    def convert_directory(
        self,
        input_dir: Union[str, Path],
        output_dir: Union[str, Path],
        source_format: str = "auto",
        target_format: str = "json",
        pattern: str = "*",
    ) -> List[Dict]:
        """Convert all files in directory"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []
        files = list(input_path.glob(pattern))

        logger.info(f"Processing {len(files)} files from {input_dir}")

        for file_path in files:
            if file_path.is_file():
                try:
                    # Generate output filename
                    output_file = output_path / f"{file_path.stem}.{target_format}"

                    # Convert file
                    result = self.converter.convert(
                        file_path, output_file, source_format, target_format
                    )
                    result["source_file"] = str(file_path)
                    results.append(result)

                    if result["success"]:
                        logger.info(f"✅ {file_path.name} → {output_file.name}")
                    else:
                        logger.error(f"❌ {file_path.name}: {result.get('error')}")

                except Exception as e:
                    logger.error(f"❌ {file_path.name}: {e}")
                    results.append(
                        {
                            "success": False,
                            "error": str(e),
                            "source_file": str(file_path),
                        }
                    )

        return results

    def convert_parallel(
        self,
        file_list: List[Union[str, Path]],
        output_dir: Union[str, Path],
        target_format: str = "json",
        max_workers: int = 4,
    ) -> List[Dict]:
        """Convert files in parallel using thread pool"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        def convert_single(file_path):
            try:
                input_path = Path(file_path)
                output_file = output_path / f"{input_path.stem}.{target_format}"
                return self.converter.convert(
                    file_path, output_file, "auto", target_format
                )
            except Exception as e:
                return {"success": False, "error": str(e), "file": str(file_path)}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(convert_single, file_path): file_path
                for file_path in file_list
            }

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    result["source_file"] = str(file_path)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Thread execution failed for {file_path}: {e}")
                    results.append(
                        {
                            "success": False,
                            "error": str(e),
                            "source_file": str(file_path),
                        }
                    )

        return results


def create_converter(languages: List[str] = None) -> UniversalConverter:
    """Factory function to create converter instance"""
    return UniversalConverter(languages)


def create_batch_converter(languages: List[str] = None) -> BatchConverter:
    """Factory function to create batch converter instance"""
    return BatchConverter(languages)
