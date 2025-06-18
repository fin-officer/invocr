"""
Dynamic extractor factory for intelligent document processing.

This module provides a dynamic decision tree approach for selecting and creating
appropriate extractors based on document classification and features.
"""

import os
from typing import Dict, List, Optional, Any, Tuple, Callable
import importlib
import inspect

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor
from invocr.formats.pdf.extractors.pdf_invoice_extractor import PDFInvoiceExtractor
from invocr.extractors.specialized.adobe_extractor import AdobeInvoiceExtractor
from invocr.formats.pdf.extractors.document_classifier import DocumentClassifier

logger = get_logger(__name__)


class DynamicExtractorFactory:
    """
    Factory for dynamically selecting and creating appropriate document extractors.
    
    This factory implements a decision tree approach to select the most appropriate
    extractor based on document classification, features, and available extractors.
    """
    
    def __init__(self):
        """Initialize the dynamic extractor factory."""
        self.classifier = DocumentClassifier()
        self.extractors = {}
        self.decision_tree = {}
        self._discover_extractors()
        self._build_decision_tree()
    
    def _discover_extractors(self):
        """
        Discover available extractors in the project.
        
        This method dynamically discovers extractor classes by searching through
        the extractors directory and registering them based on their capabilities.
        """
        # Register built-in extractors
        self.extractors["default"] = PDFInvoiceExtractor
        self.extractors["adobe_json"] = AdobeInvoiceExtractor
        
        # TODO: Dynamically discover additional extractors
        # This would scan directories and import modules to find extractor classes
        
        logger.info(f"Discovered {len(self.extractors)} extractors")
    
    def _build_decision_tree(self):
        """
        Build the decision tree for extractor selection.
        
        This method constructs a decision tree that maps document types and
        features to appropriate extractors.
        """
        # Basic decision tree structure
        self.decision_tree = {
            "adobe_json": {
                "extractor": "adobe_json",
                "confidence_threshold": 0.7
            },
            "invoice": {
                "extractor": "default",
                "subtypes": {
                    "has_tables": {
                        "true": {
                            "extractor": "default",  # Could be specialized table extractor
                            "params": {"table_mode": True}
                        },
                        "false": {
                            "extractor": "default"
                        }
                    },
                    "language": {
                        "en": {"extractor": "default"},
                        "pl": {"extractor": "default"},  # Could be language-specific
                        "de": {"extractor": "default"},
                        "fr": {"extractor": "default"},
                        "es": {"extractor": "default"}
                    }
                }
            },
            "receipt": {
                "extractor": "default",
                "params": {"receipt_mode": True}
            },
            "order": {
                "extractor": "default",
                "params": {"order_mode": True}
            }
        }
        
        logger.info("Built extractor decision tree")
    
    def create_extractor(self, text: str, metadata: Optional[Dict[str, Any]] = None,
                        rules: Optional[Dict] = None) -> Tuple[BaseInvoiceExtractor, Dict[str, Any]]:
        """
        Create an appropriate extractor based on document classification.
        
        Args:
            text: Document text content
            metadata: Optional document metadata
            rules: Optional custom extraction rules
            
        Returns:
            Tuple of (extractor_instance, classification_info)
        """
        # Classify the document
        doc_type, attributes = self.classifier.classify_document(text, metadata)
        
        # Navigate the decision tree to select the appropriate extractor
        extractor_info = self._navigate_decision_tree(doc_type, attributes)
        
        # Get the extractor class
        extractor_key = extractor_info.get("extractor", "default")
        extractor_class = self.extractors.get(extractor_key, PDFInvoiceExtractor)
        
        # Prepare parameters
        params = extractor_info.get("params", {})
        if rules:
            params["rules"] = rules
        
        # Create and return the extractor instance
        try:
            extractor = extractor_class(**params)
            logger.info(f"Created {extractor_class.__name__} for {doc_type} document")
            return extractor, {"classification": doc_type, "attributes": attributes}
        except Exception as e:
            logger.error(f"Error creating extractor: {e}")
            # Fallback to default extractor
            return PDFInvoiceExtractor(rules=rules), {"classification": doc_type, "attributes": attributes}
    
    def _navigate_decision_tree(self, doc_type: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigate the decision tree to find the appropriate extractor configuration.
        
        Args:
            doc_type: Document type from classification
            attributes: Document attributes from classification
            
        Returns:
            Dictionary with extractor information
        """
        # Start with the document type node
        if doc_type not in self.decision_tree:
            logger.warning(f"Unknown document type: {doc_type}, using default")
            return {"extractor": "default"}
        
        node = self.decision_tree[doc_type]
        
        # Check confidence threshold if specified
        if "confidence_threshold" in node and attributes.get("confidence", 0) < node["confidence_threshold"]:
            logger.info(f"Confidence below threshold, using default extractor")
            return {"extractor": "default"}
        
        # Check subtypes if available
        if "subtypes" in node:
            subtypes = node["subtypes"]
            
            # Handle boolean features
            for feature in ["has_tables", "has_line_items"]:
                if feature in subtypes and feature in attributes:
                    value = "true" if attributes[feature] else "false"
                    if value in subtypes[feature]:
                        node = subtypes[feature][value]
            
            # Handle categorical features
            for feature in ["language"]:
                if feature in subtypes and feature in attributes:
                    value = attributes[feature]
                    if value in subtypes[feature]:
                        node = subtypes[feature][value]
        
        # Return the extractor information
        result = {"extractor": node.get("extractor", "default")}
        if "params" in node:
            result["params"] = node["params"]
        
        return result
    
    def register_extractor(self, key: str, extractor_class: type) -> None:
        """
        Register a new extractor class.
        
        Args:
            key: Unique identifier for the extractor
            extractor_class: The extractor class to register
        """
        if not issubclass(extractor_class, BaseInvoiceExtractor):
            raise ValueError(f"Extractor class must inherit from BaseInvoiceExtractor")
        
        self.extractors[key] = extractor_class
        logger.info(f"Registered extractor: {key}")
    
    def update_decision_tree(self, path: List[str], node: Dict[str, Any]) -> None:
        """
        Update a specific node in the decision tree.
        
        Args:
            path: List of keys defining the path to the node
            node: New node configuration
        """
        current = self.decision_tree
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[path[-1]] = node
        logger.info(f"Updated decision tree node at path: {'/'.join(path)}")


# Singleton instance
_factory_instance = None

def get_extractor_factory() -> DynamicExtractorFactory:
    """
    Get the singleton instance of the DynamicExtractorFactory.
    
    Returns:
        DynamicExtractorFactory instance
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = DynamicExtractorFactory()
    return _factory_instance
