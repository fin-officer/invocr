"""
Document type detection system using hierarchical decision trees.

This module provides a dynamic document type detection framework that uses
a hierarchical decision tree approach to identify document types and formats.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class DetectionRule(ABC):
    """Base class for document detection rules."""
    
    def __init__(self, name: str, priority: int = 0):
        """
        Initialize a detection rule.
        
        Args:
            name: Name of the rule
            priority: Priority of the rule (higher values = higher priority)
        """
        self.name = name
        self.priority = priority
        
    @abstractmethod
    def matches(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        """
        Check if the rule matches the document.
        
        Args:
            text: Document text content
            metadata: Optional document metadata
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass


class PatternRule(DetectionRule):
    """Detection rule based on regex patterns."""
    
    def __init__(self, name: str, patterns: List[str], priority: int = 0, 
                 min_matches: int = 1, threshold: float = 0.5):
        """
        Initialize a pattern-based detection rule.
        
        Args:
            name: Name of the rule
            patterns: List of regex patterns to match
            priority: Priority of the rule
            min_matches: Minimum number of patterns that must match
            threshold: Confidence threshold for a match
        """
        super().__init__(name, priority)
        self.patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in patterns]
        self.min_matches = min_matches
        self.threshold = threshold
        
    def matches(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        """
        Check if the patterns match the document text.
        
        Args:
            text: Document text content
            metadata: Optional document metadata
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not text:
            return 0.0
            
        matches = sum(1 for pattern in self.patterns if pattern.search(text))
        
        # Calculate confidence score
        if matches < self.min_matches:
            return 0.0
            
        confidence = min(1.0, matches / len(self.patterns))
        
        return confidence if confidence >= self.threshold else 0.0


class MetadataRule(DetectionRule):
    """Detection rule based on document metadata."""
    
    def __init__(self, name: str, metadata_keys: Dict[str, List[str]], priority: int = 0):
        """
        Initialize a metadata-based detection rule.
        
        Args:
            name: Name of the rule
            metadata_keys: Dictionary mapping metadata keys to possible values
            priority: Priority of the rule
        """
        super().__init__(name, priority)
        self.metadata_keys = metadata_keys
        
    def matches(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        """
        Check if the metadata matches the rule.
        
        Args:
            text: Document text content
            metadata: Document metadata
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not metadata:
            return 0.0
            
        matches = 0
        total_keys = len(self.metadata_keys)
        
        for key, values in self.metadata_keys.items():
            if key in metadata:
                metadata_value = str(metadata[key]).lower()
                if any(value.lower() in metadata_value for value in values):
                    matches += 1
                    
        return matches / total_keys if total_keys > 0 else 0.0


class DocumentDetector:
    """
    Document detector using a hierarchical decision tree approach.
    
    This class implements a multi-level detection system that can identify
    document types and formats based on text content and metadata.
    """
    
    def __init__(self):
        """Initialize the document detector with empty rule sets."""
        self.rules: Dict[str, List[DetectionRule]] = {}
        
    def add_rule(self, document_type: str, rule: DetectionRule) -> None:
        """
        Add a detection rule for a document type.
        
        Args:
            document_type: Type of document this rule applies to
            rule: Detection rule instance
        """
        if document_type not in self.rules:
            self.rules[document_type] = []
            
        self.rules[document_type].append(rule)
        
        # Sort rules by priority (higher priority first)
        self.rules[document_type].sort(key=lambda r: r.priority, reverse=True)
        
    def detect(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, float]:
        """
        Detect document type from text content and metadata.
        
        Args:
            text: Document text content
            metadata: Optional document metadata
            
        Returns:
            Tuple of (document_type, confidence_score)
        """
        best_type = "unknown"
        best_confidence = 0.0
        all_results = {}
        
        for doc_type, type_rules in self.rules.items():
            # Apply all rules for this document type
            rule_results = []
            for rule in type_rules:
                score = rule.matches(text, metadata)
                rule_results.append({
                    'rule_name': rule.name,
                    'confidence': score,
                    'priority': rule.priority
                })
                logger.debug(f"Rule '{rule.name}' for '{doc_type}' returned confidence: {score:.2f}")
            
            # Calculate overall confidence for this document type
            if rule_results:
                # Weight by rule priority
                weighted_scores = [result['confidence'] * (result['priority'] + 1) for result in rule_results]
                total_weights = sum(rule['priority'] + 1 for rule in rule_results)
                
                type_confidence = sum(weighted_scores) / total_weights if total_weights > 0 else 0.0
                
                logger.info(f"Document type '{doc_type}' overall confidence: {type_confidence:.2f}")
                
                # Store detailed results
                all_results[doc_type] = {
                    'confidence': type_confidence,
                    'rules': rule_results
                }
                
                # Update best match if confidence is higher
                if type_confidence > best_confidence:
                    best_type = doc_type
                    best_confidence = type_confidence
        
        return best_type, best_confidence, all_results


# Create and configure default document detector
default_detector = DocumentDetector()

# Adobe invoice detection rules
adobe_patterns = [
    r"Adobe Systems Software Ireland",
    r"Invoice Number\s+\w+",
    r"Adobe Creative Cloud",
    r"PRODUCT\s+NUMBER\s+PRODUCT\s+DESCRIPTION",
    r"GRAND TO[TU]AL"  # Handles both TOTAL and TOUAL typo
]
default_detector.add_rule("adobe_invoice", PatternRule("adobe_text", adobe_patterns, priority=10, min_matches=2))
default_detector.add_rule("adobe_invoice", MetadataRule("adobe_metadata", 
                                                      {"source": ["adobe"], 
                                                       "filename": ["Adobe_Transaction"]}, 
                                                      priority=20))

# Receipt detection rules
receipt_patterns = [
    r"Receipt\s+#",
    r"GROCERIES",
    r"TOTAL:\s*\$?\d+\.\d{2}",
    r"CASH\s+REGISTER",
    r"THANK\s+YOU\s+FOR\s+SHOPPING"
]
default_detector.add_rule("receipt", PatternRule("receipt_text", receipt_patterns, priority=5, min_matches=2))

# Standard invoice detection rules
invoice_patterns = [
    r"Invoice\s+#",
    r"Bill\s+To",
    r"Payment\s+Terms",
    r"Due\s+Date",
    r"Purchase\s+Order"
]
default_detector.add_rule("invoice", PatternRule("invoice_text", invoice_patterns, priority=3, min_matches=2))

# Credit note detection rules
credit_patterns = [
    r"Credit\s+Note",
    r"Credit\s+#",
    r"Refund",
    r"\(.*?\)",  # Parenthesized amounts (negative values)
    r"-\d+\.\d{2}"  # Negative amounts
]
default_detector.add_rule("credit_note", PatternRule("credit_text", credit_patterns, priority=8, min_matches=2))


def detect_document_type(text: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, float, Dict[str, Any]]:
    """
    Detect document type using the default detector.
    
    Args:
        text: Document text content
        metadata: Optional document metadata
        
    Returns:
        Tuple of (document_type, confidence_score, detection_features)
    """
    doc_type, confidence, features = default_detector.detect(text, metadata)
    logger.info(f"Detected document type: {doc_type} (confidence: {confidence:.2f})")
    
    # Extract language information
    from invocr.utils.ocr import get_document_language_confidence
    language_scores = get_document_language_confidence(text)
    primary_language = max(language_scores.items(), key=lambda x: x[1])[0]
    
    # Add language detection to features
    features['language'] = {
        'primary': primary_language,
        'scores': language_scores
    }
    
    # Analyze document structure
    from invocr.utils.ocr import analyze_document_structure
    structure = analyze_document_structure(text)
    features['structure'] = structure
    
    return doc_type, confidence, features
