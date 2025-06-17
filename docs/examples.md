[🏠 Home](../README.md) | [📚 Documentation](./) | [📋 Examples](./examples.md) | [🔌 API](./api.md) | [💻 CLI](./cli.md)

---

# InvOCR Examples

This document provides practical examples of how to use InvOCR for various document processing tasks.

## Table of Contents
- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
- [PDF Processing](#pdf-processing)
- [OCR Processing](#ocr-processing)
- [Batch Processing](#batch-processing)
- [API Usage](#api-usage)
- [Advanced Examples](#advanced-examples)
- [Validation](#validation)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/fin-officer/invocr.git
cd invocr

# Install dependencies
poetry install

# Install Tesseract OCR (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng
```

### Basic Usage
```python
from invocr.core import PDFProcessor

# Initialize the processor
processor = PDFProcessor()

# Process a single PDF
success, error = processor.process_pdf("invoice.pdf", "output")
if success:
    print("PDF processed successfully!")
else:
    print(f"Error: {error}")
```

## PDF Processing

### Extract Text from PDF
```python
from invocr.core.pdf_processor import PDFProcessor

processor = PDFProcessor()
text, error = processor.extract_text("document.pdf")
if text:
    print(text[:500])  # Print first 500 characters
```

### Validate PDF
```python
from invocr.utils.validation import is_valid_pdf, is_valid_pdf_simple

# Simple check (fast)
if is_valid_pdf_simple("document.pdf"):
    print("File appears to be a valid PDF")

# Detailed validation
is_valid, error = is_valid_pdf("document.pdf", min_size=1024)  # 1KB minimum
if not is_valid:
    print(f"Invalid PDF: {error}")
```

## OCR Processing

### Basic OCR
```python
from invocr.core.ocr import create_ocr_engine

# Initialize OCR engine with supported languages
ocr = create_ocr_engine(["en", "pl", "de"])

# Extract text from image
result = ocr.extract_text("receipt.jpg")
print(result["text"])
```

## Batch Processing

### Process Directory of PDFs
```python
from invocr.core import PDFProcessor

processor = PDFProcessor()
results = processor.process_directory("invoices/", "output/")

print(f"Processed: {results['succeeded']} files")
print(f"Failed: {results['failed']} files")
```

## API Usage

### Start the API Server
```bash
uvicorn invocr.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Upload and Process File
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/process' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@invoice.pdf;type=application/pdf'
```

## Advanced Examples

### Custom PDF Processing Pipeline
```python
from pathlib import Path
from invocr.core import PDFProcessor
from invocr.core.ocr import create_ocr_engine
from invocr.core.extractor import create_extractor

def custom_pipeline(pdf_path, output_dir):
    # Initialize components
    pdf_processor = PDFProcessor()
    ocr_engine = create_ocr_engine(["en", "pl"])
    extractor = create_extractor()
    
    # Process PDF
    text, error = pdf_processor.extract_text(pdf_path)
    if error:
        return False, f"Text extraction failed: {error}"
    
    # Extract structured data
    data = extractor.extract_invoice_data(text)
    
    # Save results
    output_path = Path(output_dir) / f"{Path(pdf_path).stem}.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return True, str(output_path)
```

## Validation

See detailed validation examples in [validation_examples.md](./examples/validation_examples.md)

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   # Install system dependencies
   sudo apt-get install tesseract-ocr tesseract-ocr-pol
   ```

2. **PDF Text Extraction Fails**
   - Ensure the PDF is not scanned (try selecting text in your PDF viewer)
   - For scanned PDFs, use the OCR functionality

3. **Performance Issues**
   - Process large documents in batches
   - Use `is_valid_pdf_simple()` for quick validation before full processing

For more help, please [open an issue](https://github.com/fin-officer/invocr/issues).
---

### 📚 Related Documentation
- [Back to Top](#)
- [Main Documentation](../README.md)
- [All Examples](./examples.md)
- [API Reference](./api.md)
- [CLI Documentation](./cli.md)
