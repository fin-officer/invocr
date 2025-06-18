"""
Config command module.

Handles the 'config' command for managing YAML configurations.
"""

import os
import sys
import click
from pathlib import Path

from invocr.utils.logger import get_logger
from invocr.config import create_default_config, validate_config, load_config

logger = get_logger(__name__)


@click.group(name='config')
def config_command():
    """Manage YAML configurations"""
    pass


@config_command.command(name='init')
@click.option('-o', '--output', 'output_path', type=click.Path(),
              default='./config/invocr.yaml', help='Path to save default config')
def init_command(output_path):
    """Initialize a new configuration file with defaults"""
    try:
        # Create parent directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created directory: {output_dir}")
        
        # Check if file already exists
        if os.path.exists(output_path):
            if not click.confirm(f"Configuration file {output_path} already exists. Overwrite?"):
                logger.info("Aborted. Configuration not changed.")
                return
        
        # Create default configuration
        create_default_config(output_path)
        
        logger.info(f"Default configuration created at {output_path}")
        
    except Exception as e:
        logger.error(f"Error creating configuration: {str(e)}")
        sys.exit(1)


@config_command.command(name='validate')
@click.argument('config_file', type=click.Path(exists=True))
def validate_config_command(config_file):
    """Validate a configuration file"""
    try:
        # Load and validate the configuration
        config = load_config(config_file)
        
        # This will have already raised an exception if invalid
        logger.info(f"Configuration file {config_file} is valid")
        
        # Print summary of configuration
        _print_config_summary(config)
        
    except Exception as e:
        logger.error(f"Invalid configuration: {str(e)}")
        sys.exit(1)


@config_command.command(name='show')
@click.argument('config_file', type=click.Path(exists=True))
def show_config_command(config_file):
    """Show configuration file contents"""
    try:
        # Load the configuration
        config = load_config(config_file)
        
        # Print summary of configuration
        _print_config_summary(config)
        
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        sys.exit(1)


def _print_config_summary(config):
    """
    Print summary of configuration settings.
    
    Args:
        config: Configuration dictionary
    """
    logger.info("Configuration Summary:")
    
    if 'extraction' in config:
        extraction = config['extraction']
        logger.info("\nExtraction settings:")
        logger.info(f"  OCR enabled: {extraction.get('use_ocr', False)}")
        logger.info(f"  Languages: {', '.join(extraction.get('languages', []))}")
        logger.info(f"  Decision tree: {extraction.get('decision_tree', False)}")
        logger.info(f"  Preferred format: {extraction.get('preferred_format', 'json')}")
    
    if 'extractors' in config:
        extractors = config['extractors']
        logger.info("\nExtractors enabled:")
        logger.info(f"  Adobe: {extractors.get('adobe', False)}")
        logger.info(f"  Rule-based: {extractors.get('rule_based', False)}")
        logger.info(f"  ML-based: {extractors.get('ml_based', False)}")
    
    if 'output' in config:
        output = config['output']
        logger.info("\nOutput settings:")
        logger.info(f"  Format: {output.get('format', 'json')}")
        logger.info(f"  Directory: {output.get('directory', './output')}")
    
    if 'processing' in config:
        processing = config['processing']
        logger.info("\nProcessing settings:")
        logger.info(f"  Batch size: {processing.get('batch_size', 10)}")
        logger.info(f"  Parallel: {processing.get('parallel', False)}")
        logger.info(f"  Max workers: {processing.get('max_workers', 4)}")
