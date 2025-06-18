"""
Main CLI entry point.

This module provides the main entry point for the InvOCR CLI.
"""

import click
import sys
from typing import Optional

from invocr.utils.logger import get_logger
from .commands import (
    convert_command,
    extract_command,
    batch_command,
    validate_command,
    config_command
)

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


def main():
    """
    Main entry point for CLI.
    """
    try:
        cli()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
