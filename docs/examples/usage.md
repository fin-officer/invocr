# InvOCR CLI Usage Examples

This document provides practical examples for using the InvOCR CLI and REST API to process invoices and documents.

---

## Basic CLI Commands

### Show Help
```sh
invocr --help
```

### Show Version
```sh
invocr --version
```

---

## Single File Conversion

### Convert PDF to JSON
```sh
invocr convert invoice.pdf invoice.json
```

### Convert Image to JSON (OCR)
```sh
invocr img2json invoice.jpg invoice.json
```

### Convert JSON to XML
```sh
invocr json2xml invoice.json invoice.xml
```

### Convert PDF to Images (PNG/JPG)
```sh
invocr pdf2img invoice.pdf ./images/
```

---

## Batch Processing

### Batch Convert All PDFs in a Directory to JSON
```sh
invocr batch ./invoices/ ./outputs/ --input-format pdf --output-format json
```

### Batch Convert Images to JSON (with verbose output)
```sh
invocr batch ./images/ ./json/ --input-format jpg --output-format json -v
```

---

## Full Extraction Pipeline

### Run Full Pipeline (PDF → IMG → JSON → XML → HTML → PDF)
```sh
invocr pipeline input.pdf --output-dir ./results/
```

### Pipeline with Custom Config
```sh
invocr pipeline input.pdf --output-dir ./results/ -c ./custom_config.yaml
```

---

## Advanced Options

### Specify Language for Extraction
```sh
invocr convert invoice.pdf invoice.json --lang pl
```

### Use Custom Configuration File
```sh
invocr convert invoice.pdf invoice.json --config ./config.yaml
```

### Enable Verbose Logging
```sh
invocr convert invoice.pdf invoice.json --verbose
```

---

## Error Handling

### Handle Nonexistent File Gracefully
```sh
invocr convert missing.pdf output.json || echo "File not found."
```

---

## REST API Usage

### Start REST API Server
```sh
invocr serve --host 0.0.0.0 --port 8080
```

### Example: Upload PDF for Extraction (using curl)
```sh
curl -X POST -F 'file=@invoice.pdf' http://localhost:8080/api/extract
```

### Example: Get System Info from API
```sh
curl http://localhost:8080/api/info
```

---

## Real-world Scenarios

### Process All Invoices in a Folder and Save as XML
```sh
for f in ./invoices/*.pdf; do
  invocr convert "$f" "./xml/$(basename "$f" .pdf).xml"
done
```

### Run Pipeline for Multiple Languages
```sh
invocr pipeline faktura_pl.pdf --lang pl --output-dir ./results/pl/
invocr pipeline rechnung_de.pdf --lang de --output-dir ./results/de/
```

### Use in Docker (if containerized)
```sh
docker run --rm -v $(pwd)/invoices:/data invocr:latest convert /data/invoice.pdf /data/invoice.json
```

---

## Show System Info
```sh
invocr info
```

---

For more details, see the [CLI Reference](../cli.md) and [API Reference](../api.md).
