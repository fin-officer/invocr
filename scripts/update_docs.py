#!/usr/bin/env python3
"""
Script to update documentation files with consistent navigation.
"""

import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent
DOCS_DIR = ROOT_DIR / 'docs'
TEMPLATES_DIR = DOCS_DIR / '_templates'

# Read navigation templates
with open(TEMPLATES_DIR / 'nav_header.md', 'r', encoding='utf-8') as f:
    NAV_HEADER = f.read()

with open(TEMPLATES_DIR / 'nav_footer.md', 'r', encoding='utf-8') as f:
    NAV_FOOTER = f.read()

def update_file(file_path: Path):
    """Update a single markdown file with navigation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip files that already have navigation
        if '🏠 Home' in content[:200]:
            print(f"✓ Already has navigation: {file_path.relative_to(ROOT_DIR)}")
            return
        
        # Add header and footer
        new_content = f"{NAV_HEADER}{content}{NAV_FOOTER}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✓ Updated: {file_path.relative_to(ROOT_DIR)}")
        
    except Exception as e:
        print(f"✗ Error processing {file_path.relative_to(ROOT_DIR)}: {e}")

def main():
    """Update all markdown files in the docs directory."""
    # Get all markdown files in the docs directory
    md_files = list(DOCS_DIR.rglob('*.md'))
    
    # Also include README.md in the root
    readme = ROOT_DIR / 'README.md'
    if readme.exists():
        md_files.append(readme)
    
    print(f"Found {len(md_files)} markdown files to process")
    
    # Process each file
    for file_path in md_files:
        update_file(file_path)
    
    print("\nDocumentation update complete!")

if __name__ == "__main__":
    main()
