from PIL import Image, ImageDraw, ImageFont
import os

def create_receipt_image(output_path):
    # Create a new image with white background
    width, height = 400, 300
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Use default font
    try:
        font = ImageFont.truetype("Arial.ttf", 12)
    except IOError:
        font = ImageFont.load_default()
    
    # Receipt text
    receipt_text = [
        "RECEIPT #12345",
        "Date: 2025-06-17",
        "",
        "Item      Qty  Price  Total",
        "-" * 30,
        "Coffee    2    $3.50  $7.00",
        "Sandwich  1    $8.99  $8.99",
        "-" * 30,
        "Subtotal: $15.99",
        "Tax:      $1.28",
        "Total:    $17.27",
        "",
        "Thank you for your business!"
    ]
    
    # Draw text on image
    y_position = 10
    for line in receipt_text:
        draw.text((10, y_position), line, fill='black', font=font)
        y_position += 15
    
    # Save the image
    image.save(output_path)
    print(f"Receipt image saved as {os.path.abspath(output_path)}")

if __name__ == "__main__":
    create_receipt_image("receipt.jpg")
