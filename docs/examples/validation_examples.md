[🏠 Home](../README.md) | [📚 Documentation](./) | [📋 Examples](./examples.md) | [🔌 API](./api.md) | [💻 CLI](./cli.md)

---

# PDF Validation Examples

This document provides examples of how to use the PDF validation utilities in the InvOCR package.

## Table of Contents
- [Basic Validation](#basic-validation)
- [Advanced Validation with Error Messages](#advanced-validation-with-error-messages)
- [Integration with File Processing](#integration-with-file-processing)
- [Batch Processing](#batch-processing)
- [Custom Validation Rules](#custom-validation-rules)

## Basic Validation

### Simple PDF Validation
Check if a file is a PDF by verifying its header:

```python
from invocr.utils import is_valid_pdf_simple

# Check if a file is a valid PDF (header check only)
is_pdf = is_valid_pdf_simple("document.pdf")
print(f"Is valid PDF: {is_pdf}")
```

## Advanced Validation with Error Messages

### Comprehensive PDF Validation
Get detailed validation results including error messages:

```python
from invocr.utils import is_valid_pdf

# Validate PDF with detailed error messages
is_valid, error = is_valid_pdf("document.pdf")
if is_valid:
    print("PDF is valid!")
else:
    print(f"Invalid PDF: {error}")

# With custom minimum file size (in bytes)
is_valid, error = is_valid_pdf("small_file.pdf", min_size=500)  # 500 bytes minimum
```

## Integration with File Processing

### Process Only Valid PDFs
```python
from pathlib import Path
from invocr.utils import is_valid_pdf

def process_pdf(file_path):
    # Your PDF processing logic here
    print(f"Processing {file_path}")

def process_directory(directory):
    for file_path in Path(directory).glob("*.pdf"):
        if is_valid_pdf_simple(str(file_path)):  # Fast check first
            is_valid, error = is_valid_pdf(str(file_path))  # Detailed check
            if is_valid:
                process_pdf(file_path)
            else:
                print(f"Skipping invalid PDF: {file_path} - {error}")
        else:
            print(f"Not a PDF: {file_path}")
```

## Batch Processing

### Validate Multiple PDFs
```python
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from invocr.utils import is_valid_pdf

def validate_pdfs(directory, max_workers=4):
    pdf_files = list(Path(directory).glob("*.pdf"))
    valid_files = []
    invalid_files = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(
            lambda p: (str(p), *is_valid_pdf(str(p))), 
            pdf_files
        ))
    
    for file_path, is_valid, error in results:
        if is_valid:
            valid_files.append(file_path)
        else:
            invalid_files.append((file_path, error))
    
    return valid_files, invalid_files

# Usage
valid, invalid = validate_pdfs("./documents")
print(f"Valid PDFs: {len(valid)}")
print(f"Invalid PDFs: {len(invalid)}")
```

## Custom Validation Rules

### Creating a Custom Validator
```python
from invocr.utils import is_valid_pdf
from typing import List, Tuple

def custom_pdf_validator(
    file_path: str,
    min_size: int = 100,
    allowed_extensions: List[str] = None
) -> Tuple[bool, str]:
    """Custom PDF validator with additional checks."""
    
    # Check file extension
    if allowed_extensions:
        ext = file_path.lower().split('.')[-1]
        if ext != 'pdf' and ext not in allowed_extensions:
            return False, f"Invalid file extension: {ext}"
    
    # Use the built-in PDF validation
    return is_valid_pdf(file_path, min_size=min_size)

# Usage
is_valid, error = custom_pdf_validator(
    "document.pdf",
    min_size=1024,  # 1KB minimum size
    allowed_extensions=["pdf", "PDF"]
)
```

## Error Handling Examples

### Detailed Error Handling
```python
from invocr.utils import is_valid_pdf

def process_pdf_safely(file_path):
    try:
        is_valid, error = is_valid_pdf(file_path)
        if not is_valid:
            if "does not exist" in error:
                print(f"File not found: {file_path}")
            elif "too small" in error:
                print(f"File too small: {file_path}")
            elif "Invalid PDF header" in error:
                print(f"Not a valid PDF: {file_path}")
            else:
                print(f"Error processing {file_path}: {error}")
            return False
            
        # Process the valid PDF here
        print(f"Processing {file_path}")
        return True
        
    except Exception as e:
        print(f"Unexpected error with {file_path}: {str(e)}")
        return False
```

## Performance Considerations

### Fast Validation for Large Directories
When processing many files, use `is_valid_pdf_simple` for an initial fast check:

```python
from pathlib import Path
from invocr.utils import is_valid_pdf_simple, is_valid_pdf

def process_directory_fast(directory):
    for file_path in Path(directory).rglob("*.pdf"):
        file_path = str(file_path)
        
        # Fast check first
        if not is_valid_pdf_simple(file_path):
            print(f"Skipping (not a PDF): {file_path}")
            continue
            
        # Only do detailed validation if needed
        is_valid, error = is_valid_pdf(file_path)
        if is_valid:
            process_file(file_path)
        else:
            print(f"Invalid PDF: {file_path} - {error}")
```

## Integration with Web Applications

### Flask Example
```python
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from invocr.utils import is_valid_pdf
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Validate the uploaded PDF
        is_valid, error = is_valid_pdf(filepath)
        if not is_valid:
            os.remove(filepath)  # Clean up invalid file
            return jsonify({"error": f"Invalid PDF: {error}"}), 400
            
        return jsonify({"message": "File uploaded and validated successfully"})

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
```
---

### 📚 Related Documentation
- [Back to Top](#)
- [Main Documentation](../README.md)
- [All Examples](./examples.md)
- [API Reference](./api.md)
- [CLI Documentation](./cli.md)
