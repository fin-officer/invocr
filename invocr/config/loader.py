"""
Configuration loader for InvOCR.

This module provides functionality for loading YAML configuration files
and validating their structure against expected schemas.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import json
import jsonschema

from invocr.utils.logger import get_logger

logger = get_logger(__name__)

# Default configuration schema
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "extraction": {
            "type": "object",
            "properties": {
                "use_ocr": {"type": "boolean"},
                "languages": {"type": "array", "items": {"type": "string"}},
                "preferred_format": {"type": "string", "enum": ["json", "xml", "csv", "html"]},
                "decision_tree": {"type": "boolean"}
            }
        },
        "extractors": {
            "type": "object",
            "properties": {
                "adobe": {"type": "boolean"},
                "rule_based": {"type": "boolean"},
                "ml_based": {"type": "boolean"}
            }
        },
        "output": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["json", "xml", "csv", "html"]},
                "directory": {"type": "string"}
            }
        },
        "processing": {
            "type": "object",
            "properties": {
                "batch_size": {"type": "integer"},
                "parallel": {"type": "boolean"},
                "max_workers": {"type": "integer"}
            }
        }
    }
}

# Default configuration values
DEFAULT_CONFIG = {
    "extraction": {
        "use_ocr": True,
        "languages": ["eng", "pol"],
        "preferred_format": "json",
        "decision_tree": True
    },
    "extractors": {
        "adobe": True,
        "rule_based": True,
        "ml_based": False
    },
    "output": {
        "format": "json",
        "directory": "./output"
    },
    "processing": {
        "batch_size": 10,
        "parallel": True,
        "max_workers": 4
    }
}


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary with configuration
        
    Raises:
        FileNotFoundError: If config file does not exist
        yaml.YAMLError: If config file is not valid YAML
    """
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Validate the loaded configuration
        validate_config(config)
        
        # Merge with defaults for missing values
        config = _merge_with_defaults(config)
        
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}")
        raise


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration against schema.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid, raises exception otherwise
        
    Raises:
        jsonschema.exceptions.ValidationError: If config does not match schema
    """
    try:
        jsonschema.validate(instance=config, schema=CONFIG_SCHEMA)
        return True
    except jsonschema.exceptions.ValidationError as e:
        logger.error(f"Invalid configuration: {e.message}")
        raise


def create_default_config(output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Create default configuration and optionally save it to file.
    
    Args:
        output_path: Optional path to save default config
        
    Returns:
        Default configuration dictionary
    """
    if output_path:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(output_path, "w") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)
        
        logger.info(f"Default configuration saved to {output_path}")
    
    return DEFAULT_CONFIG


def _merge_with_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge provided configuration with defaults for missing values.
    
    Args:
        config: User configuration
        
    Returns:
        Merged configuration
    """
    result = DEFAULT_CONFIG.copy()
    
    for section, values in config.items():
        if section in result:
            if isinstance(values, dict) and isinstance(result[section], dict):
                # Merge section dictionaries
                for key, value in values.items():
                    result[section][key] = value
            else:
                # Replace entire section
                result[section] = values
        else:
            # Add new section
            result[section] = values
    
    return result
