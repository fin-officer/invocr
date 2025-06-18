"""
Configuration module for InvOCR.

This module provides functionality for loading and validating
YAML configuration files for extraction pipelines.
"""

from .loader import load_config, validate_config, create_default_config

__all__ = ["load_config", "validate_config", "create_default_config"]
