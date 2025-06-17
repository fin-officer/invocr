[🏠 Home](../README.md) | [📚 Documentation](./) | [📋 Examples](./examples.md) | [🔌 API](./api.md) | [💻 CLI](./cli.md)

---

# InvOCR API Documentation

## Overview

The InvOCR REST API provides endpoints for document conversion and OCR processing.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication required for local development.

## Endpoints

### Health Check

```http
GET /health
```

Returns system health status.

### System Information

```http
GET /info
```

Returns supported formats, languages, and features.

### Convert File

```http
POST /convert
```

Convert uploaded file to specified format.

**Parameters:**
- `file` (file): Input file
- `target_format` (string): Output format (json, xml, html, pdf)
- `languages` (string): Comma-separated language codes
- `async_processing` (boolean): Process in background

### Check Job Status

```http
GET /status/{job_id}
```

Get conversion job status.

### Download Result

```http
GET /download/{job_id}
```

Download conversion result.

## Example Usage

```bash
# Convert PDF to JSON
curl -X POST "http://localhost:8000/convert" \
  -F "file=@invoice.pdf" \
  -F "target_format=json"

# Check status
curl "http://localhost:8000/status/job-id"

# Download result
curl "http://localhost:8000/download/job-id" -o result.json
```
---

### 📚 Related Documentation
- [Back to Top](#)
- [Main Documentation](../README.md)
- [All Examples](./examples.md)
- [API Reference](./api.md)
- [CLI Documentation](./cli.md)
