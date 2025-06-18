"""
Unit tests for the ML-based extractor module.

This module contains tests for the specialized ML extractor functionality
to ensure it works correctly with transformer models for QA and NER tasks.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path

from invocr.formats.pdf.extractors.specialized.ml_extractor import MLExtractor, ExtractionTask
from invocr.formats.pdf.extractors.specialized.validation import DataValidator


class TestMLExtractor(unittest.TestCase):
    """Test cases for the MLExtractor class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create mock pipelines
        self.qa_pipeline_patcher = patch('invocr.formats.pdf.extractors.specialized.ml_extractor.pipeline')
        self.mock_pipeline = self.qa_pipeline_patcher.start()
        
        # Configure mock QA pipeline
        self.mock_qa_pipeline = MagicMock()
        self.mock_qa_pipeline.return_value = {
            "answer": "INV-12345",
            "score": 0.95,
            "start": 100,
            "end": 109
        }
        
        # Configure mock NER pipeline
        self.mock_ner_pipeline = MagicMock()
        self.mock_ner_pipeline.return_value = [
            {
                "entity_group": "ORG",
                "score": 0.98,
                "word": "Acme Corp",
                "start": 50,
                "end": 59
            },
            {
                "entity_group": "PER",
                "score": 0.92,
                "word": "John Smith",
                "start": 150,
                "end": 160
            }
        ]
        
        # Configure pipeline to return different mocks based on task
        def side_effect(task, **kwargs):
            if task == "question-answering":
                return self.mock_qa_pipeline
            elif task == "ner":
                return self.mock_ner_pipeline
            return MagicMock()
            
        self.mock_pipeline.side_effect = side_effect
        
        # Create extractor with mocked dependencies
        self.extractor = MLExtractor(
            model_name="test-qa-model",
            ner_model_name="test-ner-model"
        )
        
        # Sample text for testing
        self.sample_text = """
        Invoice #INV-12345
        Date: 2023-01-15
        Due Date: 2023-02-15
        
        From: Acme Corp
        Tax ID: 123456789
        
        To: John Smith
        Customer ID: CUST-001
        
        Total Amount: $1,234.56
        Tax Amount: $123.45
        """
    
    def tearDown(self):
        """Clean up after tests."""
        self.qa_pipeline_patcher.stop()
    
    def test_extract_with_qa(self):
        """Test extracting information using question answering."""
        # Test successful extraction
        value, info = self.extractor.extract_with_qa(
            self.sample_text, 
            "What is the invoice number?",
            confidence_threshold=0.5
        )
        
        # Verify results
        self.assertEqual(value, "INV-12345")
        self.assertTrue(info["success"])
        self.assertEqual(info["confidence"], 0.95)
        
        # Test extraction below confidence threshold
        self.mock_qa_pipeline.return_value = {
            "answer": "INV-12345",
            "score": 0.3,
            "start": 100,
            "end": 109
        }
        
        value, info = self.extractor.extract_with_qa(
            self.sample_text, 
            "What is the invoice number?",
            confidence_threshold=0.5
        )
        
        # Verify results
        self.assertIsNone(value)
        self.assertFalse(info["success"])
        self.assertEqual(info["confidence"], 0.3)
    
    def test_extract_with_ner(self):
        """Test extracting entities using named entity recognition."""
        # Test extracting all entities
        entities = self.extractor.extract_with_ner(self.sample_text, "")
        
        # Verify results
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0]["word"], "Acme Corp")
        self.assertEqual(entities[0]["entity_group"], "ORG")
        
        # Test extracting specific entity type
        entities = self.extractor.extract_with_ner(self.sample_text, "PER")
        
        # Verify results - should be filtered to only PER entities
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]["word"], "John Smith")
        self.assertEqual(entities[0]["entity_group"], "PER")
    
    def test_extract_field(self):
        """Test extracting a field using ML techniques."""
        # Create extraction task
        task = ExtractionTask(
            field_name="invoice_number",
            question="What is the invoice number?",
            validation_type="text",
            confidence_threshold=0.5
        )
        
        # Mock the validator to return valid=True
        with patch.object(self.extractor.validator, 'validate_field') as mock_validate:
            mock_validate.return_value = {"valid": True}
            
            # Test successful extraction and validation
            value, info = self.extractor.extract_field(self.sample_text, task)
            
            # Verify results
            self.assertEqual(value, "INV-12345")
            self.assertTrue(info["success"])
        
        # Test with validation failure
        with patch.object(self.extractor.validator, 'validate_field') as mock_validate:
            mock_validate.return_value = {"valid": False, "error": "Invalid format"}
            
            value, info = self.extractor.extract_field(self.sample_text, task)
            
            # Verify results
            self.assertIsNone(value)
            self.assertTrue(info["success"])  # QA was successful
            self.assertFalse(info["valid"])   # But validation failed
            self.assertEqual(info["validation_error"], "Invalid format")
    
    def test_extract_data(self):
        """Test extracting all data from a document."""
        # Configure mock QA pipeline to return different answers for different questions
        def qa_side_effect(question, context):
            if "invoice number" in question.lower():
                return {"answer": "INV-12345", "score": 0.95, "start": 100, "end": 109}
            elif "date" in question.lower() and "due" not in question.lower():
                return {"answer": "2023-01-15", "score": 0.92, "start": 120, "end": 130}
            elif "due date" in question.lower():
                return {"answer": "2023-02-15", "score": 0.90, "start": 150, "end": 160}
            elif "total amount" in question.lower():
                return {"answer": "$1,234.56", "score": 0.88, "start": 200, "end": 209}
            elif "tax amount" in question.lower():
                return {"answer": "$123.45", "score": 0.85, "start": 220, "end": 227}
            elif "vendor" in question.lower() or "seller" in question.lower():
                return {"answer": "Acme Corp", "score": 0.82, "start": 50, "end": 59}
            elif "customer" in question.lower() or "buyer" in question.lower():
                return {"answer": "John Smith", "score": 0.80, "start": 150, "end": 160}
            return {"answer": "", "score": 0.1, "start": 0, "end": 0}
        
        self.mock_qa_pipeline.side_effect = qa_side_effect
        
        # Mock the validator to return valid=True for all fields
        with patch.object(self.extractor.validator, 'validate_field') as mock_validate:
            mock_validate.return_value = {"valid": True}
            
            # Test extracting all data
            results = self.extractor.extract_data(self.sample_text)
            
            # Verify results
            self.assertEqual(results["invoice_number"], "INV-12345")
            self.assertEqual(results["issue_date"], "2023-01-15")
            self.assertEqual(results["due_date"], "2023-02-15")
            self.assertEqual(results["total_amount"], "$1,234.56")
            self.assertEqual(results["tax_amount"], "$123.45")
            self.assertEqual(results["vendor_name"], "Acme Corp")
            self.assertEqual(results["customer_name"], "John Smith")
        
        # Verify extraction info is present
        self.assertIn("extraction_info", results)
        self.assertIn("invoice_number", results["extraction_info"])
        
        # Verify entities are extracted
        self.assertIn("entities", results)
        self.assertEqual(len(results["entities"]), 2)
    
    def test_add_task(self):
        """Test adding a new extraction task."""
        # Get initial task count
        initial_count = len(self.extractor.tasks)
        
        # Add a new task
        self.extractor.add_task(
            field_name="custom_field",
            question="What is the custom field value?",
            validation_type="text",
            confidence_threshold=0.7
        )
        
        # Verify task was added
        self.assertEqual(len(self.extractor.tasks), initial_count + 1)
        self.assertEqual(self.extractor.tasks[-1].field_name, "custom_field")
        self.assertEqual(self.extractor.tasks[-1].question, "What is the custom field value?")
        self.assertEqual(self.extractor.tasks[-1].confidence_threshold, 0.7)
    
    def test_load_tasks_from_file(self):
        """Test loading tasks from a JSON file."""
        # Create a temporary tasks file
        tasks_data = [
            {
                "field_name": "test_field_1",
                "question": "What is test field 1?",
                "validation_type": "text",
                "confidence_threshold": 0.6
            },
            {
                "field_name": "test_field_2",
                "question": "What is test field 2?",
                "validation_type": "date",
                "confidence_threshold": 0.7
            }
        ]
        
        # Mock open to avoid file I/O
        with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(tasks_data))):
            self.extractor.load_tasks_from_file("dummy_path.json")
        
        # Verify tasks were loaded
        self.assertEqual(len(self.extractor.tasks), 2)
        self.assertEqual(self.extractor.tasks[0].field_name, "test_field_1")
        self.assertEqual(self.extractor.tasks[1].field_name, "test_field_2")
        self.assertEqual(self.extractor.tasks[0].validation_type, "text")
        self.assertEqual(self.extractor.tasks[1].validation_type, "date")


if __name__ == "__main__":
    unittest.main()
