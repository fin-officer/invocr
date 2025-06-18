"""
Adapter for dotect package.

This module re-exports functionality from the dotect package
to maintain backward compatibility with existing code.
"""

# Re-export detection functionality from dotect
from dotect.base import (
    Detector,
    DocumentDetector,
    DetectionResult,
    DocumentType
)

from dotect.rule_detector import (
    RuleBasedDetector,
    PatternMatcher,
    KeywordDetector
)

from dotect.ml_classifier import (
    MLDocumentClassifier,
    TransformerClassifier
)

from dotect.detector_factory import (
    DetectorFactory,
    UnifiedDetectorFactory
)

# For backward compatibility
from dotect import *
