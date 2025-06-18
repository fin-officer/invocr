"""
Common utilities for CLI commands.

This module provides shared functionality used by multiple CLI commands.
"""

import os
import sys
import click
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from invocr.utils.logger import get_logger
from invocr.config import load_config, validate_config, create_default_config

logger = get_logger(__name__)


def load_yaml_config(config_file: str) -> Dict[str, Any]:
    """
    Load YAML configuration file.
    
    Args:
        config_file: Path to config file
        
    Returns:
        Loaded configuration
    """
    try:
        return load_config(config_file)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)


def find_files(directory: str, extensions: List[str], recursive: bool = True) -> List[Path]:
    """
    Find files with specified extensions in directory.
    
    Args:
        directory: Directory to search
        extensions: List of file extensions to find
        recursive: Whether to search recursively
        
    Returns:
        List of file paths
    """
    directory_path = Path(directory)
    pattern = "**/*" if recursive else "*"
    
    files = []
    for ext in extensions:
        # Ensure extension starts with a dot
        if not ext.startswith("."):
            ext = f".{ext}"
        
        files.extend(directory_path.glob(f"{pattern}{ext}"))
    
    return sorted(files)


def ensure_output_dir(directory: str) -> str:
    """
    Ensure output directory exists.
    
    Args:
        directory: Directory path
        
    Returns:
        Absolute path to directory
    """
    directory_path = Path(directory).absolute()
    os.makedirs(directory_path, exist_ok=True)
    return str(directory_path)


def get_matching_output_path(input_path: str, output_dir: str, output_ext: str) -> str:
    """
    Generate output path with same name but different extension.
    
    Args:
        input_path: Input file path
        output_dir: Output directory
        output_ext: Output file extension
        
    Returns:
        Output file path
    """
    input_file = Path(input_path)
    output_file = Path(output_dir) / f"{input_file.stem}{output_ext}"
    return str(output_file)


def process_month_year_dir(base_dir: str, month: int, year: int) -> Tuple[str, str]:
    """
    Get source and output directories for month/year processing.
    
    Args:
        base_dir: Base directory
        month: Month number
        year: Year number
        
    Returns:
        Tuple of (source_dir, output_dir)
    """
    source_dir = os.path.join(base_dir, f"{year}.{month:02d}", "attachments")
    output_dir = os.path.join(base_dir, f"{year}.{month:02d}", "json")
    
    # Create directories if they don't exist
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    return source_dir, output_dir
