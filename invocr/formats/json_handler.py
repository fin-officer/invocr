"""
JSON format handler for InvOCR
Handles loading, validating, and processing JSON data
"""

import json
import logging
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

# Type variable for generic type hints
T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class JSONHandler:
    """Handler for JSON operations including validation and conversion"""

    def __init__(self, validate_schema: bool = True):
        """
        Initialize JSON handler

        Args:
            validate_schema: Whether to validate JSON against a schema
        """
        self.validate_schema = validate_schema

    def load_json(
        self, json_input: Union[str, Path, dict, list], model: Type[T] = None, **kwargs
    ) -> Union[Dict, List, T]:
        """
        Load JSON from string, file, or dict

        Args:
            json_input: JSON string, file path, or dict/list
            model: Pydantic model to validate against (optional)

        Returns:
            Parsed JSON data

        Raises:
            ValueError: If JSON is invalid or doesn't match schema
            FileNotFoundError: If file doesn't exist
        """
        try:
            # Handle file path
            if isinstance(json_input, (str, Path)) and Path(json_input).exists():
                with open(json_input, "r", encoding="utf-8") as f:
                    data = json.load(f, **kwargs)
            # Handle JSON string
            elif isinstance(json_input, str):
                data = json.loads(json_input, **kwargs)
            # Already a dict/list
            elif isinstance(json_input, (dict, list)):
                data = json_input
            else:
                raise ValueError(f"Unsupported input type: {type(json_input)}")

            # Validate against model if provided
            if model is not None:
                if isinstance(data, list):
                    return [model.model_validate(item) for item in data]
                return model.model_validate(data)

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            raise ValueError(f"Invalid JSON: {str(e)}")
        except FileNotFoundError as e:
            logger.error(f"File not found: {json_input}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise ValueError(f"Validation error: {str(e)}")

    def save_json(
        self,
        data: Any,
        output_path: Union[str, Path],
        indent: int = 2,
        ensure_ascii: bool = False,
        **kwargs,
    ) -> bool:
        """
        Save data to JSON file

        Args:
            data: Data to save (must be JSON serializable)
            output_path: Output file path
            indent: Indentation level
            ensure_ascii: Whether to escape non-ASCII characters

        Returns:
            bool: True if save was successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert Pydantic models to dicts
            if hasattr(data, "model_dump"):
                data = data.model_dump()
            elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
                data = [item.model_dump() for item in data]

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
                    indent=indent,
                    ensure_ascii=ensure_ascii,
                    default=self._json_serializer,
                    **kwargs,
                )
            return True

        except (TypeError, ValueError) as e:
            logger.error(f"Error saving JSON to {output_path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving JSON: {str(e)}")
            return False

    def validate_json(
        self,
        json_data: Union[str, dict, list],
        schema: Union[dict, Type[BaseModel]] = None,
    ) -> bool:
        """
        Validate JSON against a schema or Pydantic model

        Args:
            json_data: JSON data to validate
            schema: JSON schema or Pydantic model

        Returns:
            bool: True if valid, False otherwise
        """
        if not schema:
            return True

        try:
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                if isinstance(json_data, str):
                    json_data = json.loads(json_data)
                schema.model_validate(json_data)
                return True
            # TODO: Implement JSON Schema validation if needed
            return True

        except (ValidationError, ValueError) as e:
            logger.error(f"Validation failed: {str(e)}")
            return False

    def _json_serializer(self, obj: Any) -> Any:
        """
        Custom JSON serializer for objects not serializable by default json code

        Args:
            obj: Object to serialize

        Returns:
            JSON-serializable representation of the object
        """
        if isinstance(obj, (datetime, Enum)):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        elif hasattr(obj, "tolist"):  # For numpy arrays
            return obj.tolist()
        elif hasattr(obj, "item"):  # For numpy scalars
            return obj.item()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def prettify(self, json_data: Union[str, dict, list], indent: int = 2) -> str:
        """
        Convert JSON data to a pretty-printed string

        Args:
            json_data: JSON data to format
            indent: Indentation level

        Returns:
            Formatted JSON string
        """
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        return json.dumps(
            json_data, indent=indent, ensure_ascii=False, default=self._json_serializer
        )

    def extract_values(self, json_data: Union[str, dict, list], key: str) -> list:
        """
        Extract all values for a given key from JSON data

        Args:
            json_data: JSON data to search in
            key: Key to search for

        Returns:
            List of values found for the key
        """
        if isinstance(json_data, str):
            json_data = json.loads(json_data)

        results = []

        def _extract(obj, k):
            if isinstance(obj, dict):
                for obj_key, obj_value in obj.items():
                    if obj_key == k:
                        results.append(obj_value)
                    _extract(obj_value, k)
            elif isinstance(obj, list):
                for item in obj:
                    _extract(item, k)

        _extract(json_data, key)
        return results

    def filter_json(
        self,
        json_data: Union[str, dict, list],
        include_keys: list = None,
        exclude_keys: list = None,
        **filters,
    ) -> Union[dict, list]:
        """
        Filter JSON data based on keys and values

        Args:
            json_data: JSON data to filter
            include_keys: List of keys to include (None for all)
            exclude_keys: List of keys to exclude
            **filters: Key-value pairs to filter by

        Returns:
            Filtered JSON data
        """
        if isinstance(json_data, str):
            json_data = json.loads(json_data)

        if isinstance(json_data, list):
            return [
                self.filter_json(item, include_keys, exclude_keys, **filters)
                for item in json_data
            ]

        if not isinstance(json_data, dict):
            return json_data

        result = {}

        for key, value in json_data.items():
            # Skip excluded keys
            if exclude_keys and key in exclude_keys:
                continue

            # Include only specified keys
            if include_keys and key not in include_keys:
                continue

            # Apply filters
            if filters:
                filter_match = True
                for filter_key, filter_value in filters.items():
                    if key == filter_key and value != filter_value:
                        filter_match = False
                        break
                if not filter_match:
                    continue

            # Recursively filter nested structures
            if isinstance(value, (dict, list)):
                value = self.filter_json(value, include_keys, exclude_keys, **filters)

            result[key] = value

        return result
