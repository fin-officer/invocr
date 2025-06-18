"""
Machine Learning based extractor for document data extraction.

This module provides ML-based extraction capabilities for documents,
leveraging pre-trained models and transformers for intelligent extraction.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
from transformers import AutoModelForSequenceClassification, AutoModelForQuestionAnswering

from invocr.utils.logger import get_logger
from invocr.formats.pdf.extractors.base_extractor import BaseInvoiceExtractor
from invocr.formats.pdf.extractors.specialized.validation import DataValidator

logger = get_logger(__name__)


@dataclass
class ExtractionTask:
    """Data class for ML extraction tasks."""
    field_name: str
    question: str
    validation_type: str = "text"
    context_window: int = 500
    confidence_threshold: float = 0.5
    description: str = ""


class MLExtractor(BaseInvoiceExtractor):
    """
    Machine Learning based extractor for document data.
    
    This extractor uses pre-trained transformer models to extract
    information from documents using question answering and NER techniques.
    """
    
    def __init__(self, model_name: str = "distilbert-base-cased-distilled-squad",
                 ner_model_name: str = "dslim/bert-base-NER",
                 tasks: Optional[List[ExtractionTask]] = None,
                 use_gpu: bool = False):
        """
        Initialize the ML extractor.
        
        Args:
            model_name: Name of the QA model to use
            ner_model_name: Name of the NER model to use
            tasks: List of extraction tasks
            use_gpu: Whether to use GPU for inference
        """
        super().__init__()
        self.logger = logger
        self.validator = DataValidator()
        self.model_name = model_name
        self.ner_model_name = ner_model_name
        self.use_gpu = use_gpu
        
        # Initialize models
        self._initialize_models()
        
        # Default extraction tasks
        self._default_tasks = [
            ExtractionTask(
                field_name="invoice_number",
                question="What is the invoice number?",
                validation_type="text",
                description="Invoice number"
            ),
            ExtractionTask(
                field_name="issue_date",
                question="What is the invoice date or issue date?",
                validation_type="date",
                description="Invoice issue date"
            ),
            ExtractionTask(
                field_name="due_date",
                question="What is the payment due date?",
                validation_type="date",
                description="Payment due date"
            ),
            ExtractionTask(
                field_name="total_amount",
                question="What is the total amount of the invoice?",
                validation_type="currency",
                description="Total invoice amount"
            ),
            ExtractionTask(
                field_name="tax_amount",
                question="What is the tax amount or VAT amount?",
                validation_type="currency",
                description="Tax amount"
            ),
            ExtractionTask(
                field_name="vendor_name",
                question="What is the name of the vendor or seller?",
                validation_type="text",
                description="Vendor name"
            ),
            ExtractionTask(
                field_name="customer_name",
                question="What is the name of the customer or buyer?",
                validation_type="text",
                description="Customer name"
            )
        ]
        
        # Initialize tasks
        self.tasks = tasks or self._default_tasks
    
    def _initialize_models(self) -> None:
        """Initialize the ML models."""
        try:
            # Initialize QA model
            self.logger.info(f"Initializing QA model: {self.model_name}")
            device = 0 if self.use_gpu else -1
            self.qa_pipeline = pipeline(
                "question-answering",
                model=self.model_name,
                tokenizer=self.model_name,
                device=device
            )
            
            # Initialize NER model
            self.logger.info(f"Initializing NER model: {self.ner_model_name}")
            self.ner_pipeline = pipeline(
                "ner",
                model=self.ner_model_name,
                tokenizer=self.ner_model_name,
                device=device,
                aggregation_strategy="simple"
            )
            
            self.logger.info("Models initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing models: {e}")
            raise
    
    def extract_with_qa(self, text: str, question: str, 
                       confidence_threshold: float = 0.5) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Extract information using question answering.
        
        Args:
            text: Document text
            question: Question to ask
            confidence_threshold: Minimum confidence score
            
        Returns:
            Tuple of (extracted_value, extraction_info)
        """
        extraction_info = {
            "question": question,
            "method": "qa",
            "success": False
        }
        
        try:
            # Limit text length to avoid token limits
            if len(text) > 10000:
                text = text[:10000]
            
            # Get answer from QA model
            result = self.qa_pipeline(question=question, context=text)
            
            answer = result["answer"].strip()
            score = result["score"]
            
            extraction_info.update({
                "confidence": score,
                "start": result["start"],
                "end": result["end"],
                "success": score >= confidence_threshold
            })
            
            if score >= confidence_threshold:
                return answer, extraction_info
            else:
                self.logger.info(f"QA confidence too low: {score} < {confidence_threshold}")
                return None, extraction_info
        
        except Exception as e:
            self.logger.error(f"Error in QA extraction: {e}")
            extraction_info["error"] = str(e)
            return None, extraction_info
    
    def extract_with_ner(self, text: str, entity_type: str) -> List[Dict[str, Any]]:
        """
        Extract entities using named entity recognition.
        
        Args:
            text: Document text
            entity_type: Type of entity to extract
            
        Returns:
            List of extracted entities with scores
        """
        try:
            # Limit text length to avoid token limits
            if len(text) > 10000:
                text = text[:10000]
            
            # Get entities from NER model
            entities = self.ner_pipeline(text)
            
            # Filter by entity type if specified
            if entity_type:
                entities = [e for e in entities if e["entity_group"] == entity_type]
            
            return entities
        
        except Exception as e:
            self.logger.error(f"Error in NER extraction: {e}")
            return []
    
    def extract_field(self, text: str, task: ExtractionTask) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Extract a field using the appropriate ML technique.
        
        Args:
            text: Document text
            task: Extraction task
            
        Returns:
            Tuple of (extracted_value, extraction_info)
        """
        self.logger.info(f"Extracting field: {task.field_name}")
        
        # Extract using QA
        value, extraction_info = self.extract_with_qa(
            text, task.question, task.confidence_threshold
        )
        
        if value:
            # Validate the extracted value
            validation_result = self.validator.validate_field(
                task.field_name, value, task.validation_type
            )
            
            extraction_info["valid"] = validation_result["valid"]
            if not validation_result["valid"]:
                extraction_info["validation_error"] = validation_result.get("error", "Validation failed")
                self.logger.warning(f"Validation failed for {task.field_name}: {value}")
                
                # If validation fails, return None
                if not validation_result["valid"]:
                    return None, extraction_info
        
        return value, extraction_info
    
    def extract_data(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract data from document text using ML techniques.
        
        Args:
            text: Document text content
            metadata: Optional document metadata
            
        Returns:
            Dictionary of extracted fields
        """
        metadata = metadata or {}
        results = {
            "metadata": metadata,
            "extraction_info": {}
        }
        
        # Extract each field
        for task in self.tasks:
            value, extraction_info = self.extract_field(text, task)
            
            if value:
                results[task.field_name] = value
            
            results["extraction_info"][task.field_name] = extraction_info
        
        # Extract entities with NER
        try:
            entities = self.extract_with_ner(text, "")
            results["entities"] = entities
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
        
        return results
    
    def add_task(self, field_name: str, question: str, validation_type: str = "text",
                context_window: int = 500, confidence_threshold: float = 0.5,
                description: str = "") -> None:
        """
        Add a new extraction task.
        
        Args:
            field_name: Name of the field to extract
            question: Question to ask
            validation_type: Type of validation to apply
            context_window: Context window size
            confidence_threshold: Minimum confidence score
            description: Description of the field
        """
        task = ExtractionTask(
            field_name=field_name,
            question=question,
            validation_type=validation_type,
            context_window=context_window,
            confidence_threshold=confidence_threshold,
            description=description
        )
        
        self.tasks.append(task)
        self.logger.info(f"Added extraction task for field '{field_name}'")
    
    def load_tasks_from_file(self, file_path: str) -> None:
        """
        Load extraction tasks from a JSON file.
        
        Args:
            file_path: Path to the JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
            
            tasks = []
            for task_data in tasks_data:
                task = ExtractionTask(
                    field_name=task_data["field_name"],
                    question=task_data["question"],
                    validation_type=task_data.get("validation_type", "text"),
                    context_window=task_data.get("context_window", 500),
                    confidence_threshold=task_data.get("confidence_threshold", 0.5),
                    description=task_data.get("description", "")
                )
                tasks.append(task)
            
            self.tasks = tasks
            self.logger.info(f"Loaded {len(tasks)} tasks from {file_path}")
        except Exception as e:
            self.logger.error(f"Error loading tasks from {file_path}: {e}")
            raise
