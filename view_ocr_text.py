import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
import sys

def extract_text_from_pdf(pdf_path):
    # Convert PDF to images
    images = convert_from_path(pdf_path)
    text = ""
    for i, image in enumerate(images):
        # Convert PIL image to OpenCV format
        open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        # Extract text using Tesseract
        page_text = pytesseract.image_to_string(open_cv_image, lang='pol+eng+deu')
        text += f"\n--- PAGE {i+1} ---\n{page_text}"
    return text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python view_ocr_text.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    text = extract_text_from_pdf(pdf_path)
    print(text)
