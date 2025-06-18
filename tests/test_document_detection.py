"""
Tests for the document detection and extraction selection system.
"""

import unittest
from unittest.mock import patch, MagicMock

from invocr.core.detection.document_detector import DocumentDetector, PatternRule, MetadataRule
from invocr.core.detection.extractor_selector import ExtractorSelector
from invocr.core.workflow.extraction_pipeline import ExtractionPipeline


class TestDocumentDetection(unittest.TestCase):
    """Test cases for document detection system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = DocumentDetector()
        
        # Add test rules
        self.detector.add_rule("test_invoice", PatternRule("test_pattern", 
                                                         ["Invoice", "Total"], 
                                                         priority=5))
        self.detector.add_rule("test_receipt", PatternRule("test_receipt", 
                                                         ["Receipt", "Thank you"], 
                                                         priority=3))
        
    def test_pattern_rule_matching(self):
        """Test pattern rule matching."""
        # Create a test rule
        rule = PatternRule("test", ["apple", "banana"], min_matches=1)
        
        # Test matching
        self.assertGreater(rule.matches("I have an apple"), 0)
        self.assertGreater(rule.matches("I have a banana"), 0)
        self.assertGreater(rule.matches("I have an apple and a banana"), 0)
        self.assertEqual(rule.matches("I have an orange"), 0)
        
    def test_metadata_rule_matching(self):
        """Test metadata rule matching."""
        # Create a test rule
        rule = MetadataRule("test", {"source": ["adobe"], "type": ["invoice"]})
        
        # Test matching
        self.assertGreater(rule.matches("", {"source": "adobe", "type": "invoice"}), 0)
        self.assertGreater(rule.matches("", {"source": "adobe", "type": "other"}), 0)
        self.assertEqual(rule.matches("", {"source": "other"}), 0)
        
    def test_document_type_detection(self):
        """Test document type detection."""
        # Test invoice detection
        doc_type, confidence = self.detector.detect("This is an Invoice with a Total of $100")
        self.assertEqual(doc_type, "test_invoice")
        self.assertGreater(confidence, 0)
        
        # Test receipt detection
        doc_type, confidence = self.detector.detect("Receipt #1234. Thank you for shopping!")
        self.assertEqual(doc_type, "test_receipt")
        self.assertGreater(confidence, 0)
        
        # Test unknown document
        doc_type, confidence = self.detector.detect("This is some random text")
        self.assertEqual(doc_type, "unknown")
        
    def test_rule_priority(self):
        """Test that rules with higher priority are preferred."""
        # Add a high-priority rule that matches the same text
        self.detector.add_rule("high_priority", PatternRule("high", 
                                                          ["Invoice"], 
                                                          priority=10))
        
        # Test that high priority rule is preferred
        doc_type, confidence = self.detector.detect("This is an Invoice")
        self.assertEqual(doc_type, "high_priority")


class TestExtractorSelector(unittest.TestCase):
    """Test cases for extractor selection system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.selector = ExtractorSelector()
        
    @patch('invocr.core.detection.extractor_selector.detect_document_type')
    @patch('invocr.formats.pdf.extractors.pdf_invoice_extractor.PDFInvoiceExtractor')
    def test_extractor_selection(self, mock_extractor_class, mock_detect):
        """Test extractor selection based on document type."""
        # Mock the document type detection
        mock_detect.return_value = "invoice"
        
        # Mock the extractor instance
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        
        # Test extractor selection
        extractor = self.selector.select_extractor("Test invoice text")
        
        # Verify that the correct extractor was created
        mock_extractor_class.assert_called_once()
        self.assertEqual(extractor, mock_extractor)
        
    def test_rule_merging(self):
        """Test that custom rules are merged with default rules."""
        # Register default rules
        self.selector.register_rules("test_type", {"field1": "pattern1"})
        
        # Create a mock extractor class
        mock_extractor_class = MagicMock()
        self.selector.register_extractor("test_type", mock_extractor_class)
        
        # Select extractor with custom rules
        self.selector.select_extractor("text", document_type="test_type", 
                                      rules={"field2": "pattern2"})
        
        # Verify that rules were merged
        call_args = mock_extractor_class.call_args[1]
        self.assertIn("rules", call_args)
        merged_rules = call_args["rules"]
        self.assertIn("field1", merged_rules)
        self.assertIn("field2", merged_rules)


class TestExtractionPipeline(unittest.TestCase):
    """Test cases for extraction pipeline."""
    
    @patch('invocr.core.detection.document_detector.detect_document_type')
    @patch('invocr.core.detection.extractor_selector.create_extractor')
    @patch('invocr.core.validators.extraction_validator.validate_extraction')
    def test_pipeline_flow(self, mock_validate, mock_create_extractor, mock_detect):
        """Test the complete pipeline flow."""
        # Mock document detection
        mock_detect.return_value = "test_type"
        
        # Mock extractor
        mock_extractor = MagicMock()
        mock_extractor.extract_invoice_data.return_value = {"invoice_number": "123"}
        mock_create_extractor.return_value = mock_extractor
        
        # Mock validation
        mock_validate.return_value = {"overall_confidence": 0.9, "is_valid": True}
        
        # Create pipeline and process document
        pipeline = ExtractionPipeline()
        result = pipeline.process_document("Test document text")
        
        # Verify pipeline flow
        mock_detect.assert_called_once()
        mock_create_extractor.assert_called_once()
        mock_extractor.extract_invoice_data.assert_called_once()
        mock_validate.assert_called_once()
        
        # Verify result structure
        self.assertIn("invoice_number", result)
        self.assertIn("validation", result)
        self.assertEqual(result["invoice_number"], "123")


if __name__ == "__main__":
    unittest.main()
