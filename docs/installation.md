# Installation Guide

## Requirements

- Python 3.9+
- Poetry (dependency management)
- Tesseract OCR with language packs (for OCR functionality)

## Basic Installation

### 1. Clone the repository

```bash
git clone https://github.com/fin-officer/invocr.git
cd invocr
```

### 2. Install with Poetry

```bash
# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

### 3. Install Tesseract OCR

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install tesseract-ocr
# Install additional language packs as needed
sudo apt install tesseract-ocr-eng tesseract-ocr-pol tesseract-ocr-deu tesseract-ocr-fra
```

#### macOS

```bash
brew install tesseract
# Install additional language packs
brew install tesseract-lang
```

#### Windows

1. Download and install Tesseract from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
2. Add Tesseract to your PATH
3. Download language data files from [GitHub](https://github.com/tesseract-ocr/tessdata) and place them in the Tesseract tessdata directory

### 4. Verify Installation

```bash
# Check if Tesseract is installed correctly
tesseract --version

# Verify InvOCR installation
poetry run invocr --version
```

## Advanced Installation

### Custom Configuration

You can customize InvOCR behavior by creating a configuration file:

```bash
# Create default configuration
poetry run invocr config init --output ./config/invocr.yaml

# Use custom configuration
poetry run invocr --config ./config/invocr.yaml convert invoice.pdf invoice.json
```

### Development Installation

For development purposes, install with development dependencies:

```bash
poetry install --with dev
```

## Troubleshooting

### Tesseract Not Found

If you encounter "Tesseract not found" errors:

1. Verify Tesseract is installed: `tesseract --version`
2. Check your PATH environment variable
3. Set the environment variable: `export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/` (adjust path as needed)

### Missing Language Packs

If you see "Warning: Invalid language" errors:

1. Check available languages: `tesseract --list-langs`
2. Install the required language pack for your OS
3. For custom language packs, download from [GitHub](https://github.com/tesseract-ocr/tessdata) and place in the Tesseract tessdata directory
