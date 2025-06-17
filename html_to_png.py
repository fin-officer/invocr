#!/usr/bin/env python3
import os
import sys
import time
import argparse
from pathlib import Path

try:
    import imgkit
except ImportError:
    print("Error: imgkit is not installed. Please install it with:")
    print("pip install imgkit")
    print("You also need to install wkhtmltopdf:")
    print("On Ubuntu/Debian: sudo apt-get install wkhtmltopdf")
    print("On macOS: brew install wkhtmltopdf")
    sys.exit(1)

def convert_html_to_png(html_dir, output_dir=None, width=900, height=1600, delay=1):
    """
    Convert all HTML files in the specified directory to PNG images.
    
    Args:
        html_dir (str): Path to directory containing HTML files
        output_dir (str, optional): Directory to save PNG files. Defaults to 'png' subdirectory.
        width (int): Viewport width in pixels
        height (int): Viewport height in pixels
        delay (int): Seconds to wait for JavaScript to execute
    """
    # Set default output directory if not specified
    if output_dir is None:
        output_dir = os.path.join(html_dir, '..', 'png')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all HTML files in the directory
    html_files = sorted(list(Path(html_dir).glob('*.html')))
    
    if not html_files:
        print(f"No HTML files found in {html_dir}")
        return
    
    total_files = len(html_files)
    print(f"Found {total_files} HTML files to convert...")
    
    # Configure imgkit options
    options = {
        'format': 'png',
        'encoding': 'UTF-8',
        'quiet': '',
        'enable-local-file-access': None,  # Allow loading local files
        'width': width,
        'height': height,
        'javascript-delay': str(delay * 1000),  # Convert to milliseconds
        'load-error-handling': 'skip',    # Skip pages with load errors
        'load-media-error-handling': 'skip',  # Skip media load errors
        'no-images': None,                # Don't load images for faster conversion
    }
    
    successful = 0
    failed = 0
    
    # Convert each HTML file to PNG
    for i, html_file in enumerate(html_files, 1):
        try:
            # Create output filename
            png_file = os.path.join(output_dir, f"{html_file.stem}.png")
            
            # Skip if PNG already exists and is newer than HTML
            if os.path.exists(png_file) and \
               os.path.getmtime(html_file) <= os.path.getmtime(png_file):
                print(f"[{i}/{total_files}] Skipping (up to date): {html_file.name}")
                successful += 1
                continue
                
            print(f"[{i}/{total_files}] Converting: {html_file.name} -> {os.path.basename(png_file)}")
            
            # Convert HTML to PNG
            imgkit.from_file(
                str(html_file),
                output_path=png_file,
                options=options
            )
            
            # Verify the output file was created
            if os.path.exists(png_file) and os.path.getsize(png_file) > 0:
                successful += 1
            else:
                print(f"  Error: Failed to create {png_file}")
                failed += 1
                
        except Exception as e:
            print(f"  Error converting {html_file.name}: {str(e)}")
            failed += 1
    
    # Print summary
    print("\nConversion complete!")
    print(f"Successfully converted: {successful} files")
    if failed > 0:
        print(f"Failed to convert: {failed} files")
    print(f"Output directory: {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert HTML emails to PNG images')
    parser.add_argument('--html-dir', default='./html', help='Directory containing HTML files (default: ./html)')
    parser.add_argument('--output-dir', help='Directory to save PNG files (default: ../png)')
    parser.add_argument('--width', type=int, default=900, help='Viewport width in pixels (default: 1200)')
    parser.add_argument('--height', type=int, default=1600, help='Viewport height in pixels (default: 800)')
    parser.add_argument('--delay', type=int, default=2, help='Seconds to wait for JavaScript (default: 2)')
    parser.add_argument('--month', type=int, help='Month to process (1-12)')
    parser.add_argument('--year', type=int, help='Year to process (e.g., 2025)')
    
    args = parser.parse_args()
    
    # If month and year are provided, use them to construct the HTML directory
    if args.month and args.year:
        pathname = os.path.dirname(os.path.abspath(__file__))
        month_str = f"{args.month:02d}"  # Ensure two-digit month
        html_dir = os.path.join(pathname, f'{args.year}.{month_str}', 'html')
        output_dir = os.path.join(pathname, f'{args.year}.{month_str}', 'png')
        
        print(f"Processing HTML files from: {html_dir}")
        print(f"Saving PNG files to: {output_dir}")
        
        # Convert HTML to PNG with auto-determined directories
        convert_html_to_png(
            html_dir=html_dir,
            output_dir=output_dir,
            width=args.width,
            height=args.height,
            delay=args.delay
        )
    else:
        # Use the provided or default directories
        convert_html_to_png(
            html_dir=args.html_dir,
            output_dir=args.output_dir,
            width=args.width,
            height=args.height,
            delay=args.delay
        )
