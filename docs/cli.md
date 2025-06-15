# CLI documentation

# InvOCR CLI Documentation

## Installation

```bash
poetry install
```

## Usage

### Basic Commands

```bash
# Show help
invocr --help

# Convert single file
invocr convert input.pdf output.json

# Convert with specific languages
invocr convert -l en,pl,de document.pdf output.json

# Convert PDF to images
invocr pdf2img document.pdf ./images/

# Image to JSON (OCR)
invocr img2json scan.png data.json

# JSON to XML
invocr json2xml data.json invoice.xml

# Batch processing
invocr batch ./pdfs/ ./output/ --format json

# Full pipeline
invocr pipeline document.pdf ./results/

# Start API server
invocr serve
```

### Advanced Options

```bash
# Batch processing with parallelization
invocr batch ./input/ ./output/ --parallel 8 --format xml

# Custom OCR languages
invocr img2json scan.png data.json --languages en,pl,de,fr

# Custom templates
invocr convert data.json invoice.html --template classic

# API server with custom host/port
invocr serve --host 0.0.0.0 --port 9000
```

### Examples

```bash
# Convert invoice PDF to JSON
invocr convert invoice.pdf invoice.json

# Process receipt image
invocr img2json receipt.jpg receipt.json --doc-type receipt

# Generate EU standard XML
invocr json2xml invoice.json eu_invoice.xml

# Create HTML invoice
invocr json2html invoice.json invoice.html --template modern
```