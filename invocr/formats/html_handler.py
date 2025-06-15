"""
HTML format handler for InvOCR
Handles conversion between JSON and HTML formats
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape


class HTMLHandler:
    """Handler for HTML operations including rendering and parsing"""

    def __init__(self, template_dir: str = None):
        """Initialize HTML handler with template directory"""
        # Default to package templates directory if not specified
        if template_dir is None:
            template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"
            )

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def json_to_html(
        self, json_data: Union[Dict, str, Path], template_name: str = "invoice.html"
    ) -> str:
        """
        Convert JSON data to HTML using a template

        Args:
            json_data: JSON data as dict, JSON string, or path to JSON file
            template_name: Name of the template file to use

        Returns:
            Rendered HTML as string
        """
        # Load JSON data if it's a file path
        if isinstance(json_data, (str, Path)):
            if Path(json_data).exists():
                with open(json_data, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = json.loads(json_data)
        else:
            data = json_data

        # Load and render template
        template = self.env.get_template(template_name)
        return template.render(**data)

    def html_to_json(
        self, html_content: str, extract_patterns: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from HTML content

        Args:
            html_content: HTML content as string
            extract_patterns: Dictionary of CSS/XPath selectors

        Returns:
            Dictionary containing extracted data
        """
        # TODO: Implement HTML parsing logic
        # This is a placeholder implementation
        return {
            "status": "success",
            "message": "HTML to JSON conversion not yet implemented",
            "data": {},
        }

    def render_template(self, template_name: str, **context) -> str:
        """
        Render a template with the given context

        Args:
            template_name: Name of the template file
            **context: Variables to pass to the template

        Returns:
            Rendered template as string
        """
        template = self.env.get_template(template_name)
        return template.render(**context)
