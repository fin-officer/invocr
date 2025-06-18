"""
InvOCR command-line interface entry point.

This module serves as the entry point for the invocr CLI, allowing commands like:
`poetry run invocr convert ...`
"""

import sys
import click
from invocr.utils.logger import get_logger
from invocr.cli.commands import (
    convert_command,
    extract_command,
    batch_command,
    validate_command,
    config_command,
    debug_command,
    ocr_text_command,
    workflow_command,
    pdf2json_command
)

# Initialize logger
logger = get_logger(__name__)

@click.group()
@click.version_option(message="InvOCR Version %(version)s")
def cli():
    """
    InvOCR - Intelligent Invoice Processing CLI.
    
    Process invoices, receipts, and financial documents with OCR and data extraction.
    """
    pass

# Register commands
cli.add_command(convert_command)
cli.add_command(extract_command)
cli.add_command(batch_command)
cli.add_command(validate_command)
cli.add_command(config_command)
cli.add_command(debug_command)
cli.add_command(ocr_text_command)
cli.add_command(workflow_command)
cli.add_command(pdf2json_command)

def main():
    """Main entry point for CLI."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
