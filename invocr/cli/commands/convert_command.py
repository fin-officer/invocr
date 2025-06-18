"""
Convert command module.

Handles the 'convert' command for converting files between formats.
"""

import os
import sys
import click
from pathlib import Path

from invocr.utils.logger import get_logger
from invocr.core.converter import convert_document
from ..common import load_yaml_config

logger = get_logger(__name__)


@click.command(name='convert')
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('-f', '--format', 'output_format', type=click.Choice(['json', 'xml', 'html', 'pdf']), 
              help='Output format')
@click.option('-l', '--languages', help='OCR languages (e.g., en,pl,de)')
@click.option('-t', '--template', help='Template for HTML/XML output')
@click.option('-c', '--config', 'config_file', type=click.Path(exists=True), 
              help='Path to YAML configuration file')
def convert_command(input_file, output_file, output_format, languages, template, config_file):
    """Convert single file between formats"""
    try:
        # Load configuration if provided
        config = None
        if config_file:
            config = load_yaml_config(config_file)
            
            # Use config values if command-line options not provided
            if not output_format and 'output' in config and 'format' in config['output']:
                output_format = config['output']['format']
                
            if not languages and 'extraction' in config and 'languages' in config['extraction']:
                languages = ','.join(config['extraction']['languages'])
        
        # Guess output format from extension if not specified
        if not output_format:
            ext = Path(output_file).suffix.lower()
            if ext == '.json':
                output_format = 'json'
            elif ext == '.xml':
                output_format = 'xml'
            elif ext == '.html':
                output_format = 'html'
            elif ext == '.pdf':
                output_format = 'pdf'
            else:
                output_format = 'json'  # Default
        
        # Parse languages
        lang_list = None
        if languages:
            lang_list = [lang.strip() for lang in languages.split(',')]
        
        # Perform conversion
        result, error = convert_document(
            input_file=input_file,
            output_file=output_file,
            output_format=output_format,
            languages=lang_list,
            template=template
        )
        
        if not result:
            logger.error(f"Conversion failed: {error}")
            sys.exit(1)
            
        logger.info(f"Successfully converted {input_file} to {output_file}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
