from PIL import Image, ImageDraw, ImageFont
import os

# Create a new image with white background
width, height = 400, 300
image = Image.new('RGB', (width, height), 'white')
draw = ImageDraw.Draw(image)

# Use default font (you might need to install a specific font for better results)
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 12)
except IOError:
    font = ImageFont.load_default()

# Receipt text
receipt_text = """RECEIPT #12345
Date: 2025-06-17

Item      Qty  Price  Total
----------------------------
Coffee    2    $3.50  $7.00
Sandwich  1    $8.99  $8.99
----------------------------
Subtotal: $15.99
Tax:      $1.28
Total:    $17.27

Thank you for your business!"""

# Draw text on image
y_position = 10
for line in receipt_text.split('\n'):
    draw.text((10, y_position), line, fill='black', font=font)
    y_position += 15  # Adjust line spacing

# Save the image
output_path = "receipt.jpg"
image.save(output_path)
print(f"Receipt image saved as {os.path.abspath(output_path)}")
