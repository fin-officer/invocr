"""
Pydantic models for API request/response validation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ConversionRequest(BaseModel):
    """Request model for file conversion"""

    target_format: str = Field(..., description="Target format (json, xml, html, pdf)")
    languages: Optional[List[str]] = Field(None, description="OCR languages")
    template: str = Field("modern", description="Template for HTML/XML output")
    async_processing: bool = Field(False, description="Process in background")


class ConversionResponse(BaseModel):
    """Response model for file conversion"""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Conversion status")
    message: str = Field(..., description="Status message")
    download_url: Optional[str] = Field(None, description="Download URL for result")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Conversion metadata")


class BatchConversionRequest(BaseModel):
    """Request model for batch conversion"""

    file_urls: List[HttpUrl] = Field(..., description="List of file URLs to convert")
    target_format: str = Field(..., description="Target format")
    languages: Optional[List[str]] = Field(None, description="OCR languages")
    parallel_workers: int = Field(4, description="Number of parallel workers")


class BatchConversionResponse(BaseModel):
    """Response model for batch conversion"""

    job_id: str = Field(..., description="Batch job identifier")
    status: str = Field(..., description="Batch status")
    message: str = Field(..., description="Status message")
    total_files: int = Field(..., description="Total files to process")
    completed_files: int = Field(0, description="Files completed")
    results_url: str = Field(..., description="URL to get batch results")


class ConversionStatus(BaseModel):
    """Model for job status"""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current status")
    progress: int = Field(0, description="Progress percentage (0-100)")
    message: str = Field("", description="Status message")
    created_at: str = Field(..., description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")
    services: Dict[str, str] = Field(..., description="Service statuses")


class SystemInfo(BaseModel):
    """System information response"""

    version: str = Field(..., description="API version")
    supported_formats: Dict[str, List[str]] = Field(
        ..., description="Supported formats"
    )
    supported_languages: List[str] = Field(..., description="Supported OCR languages")
    max_file_size: str = Field(..., description="Maximum file size")
    features: List[str] = Field(..., description="Available features")


class InvoiceData(BaseModel):
    """Model for extracted invoice data"""

    document_number: str = Field("", description="Invoice/document number")
    document_date: str = Field("", description="Document date")
    due_date: str = Field("", description="Payment due date")

    class SellerInfo(BaseModel):
        name: str = ""
        address: str = ""
        tax_id: str = ""
        phone: str = ""
        email: str = ""

    class BuyerInfo(BaseModel):
        name: str = ""
        address: str = ""
        tax_id: str = ""
        phone: str = ""
        email: str = ""

    class LineItem(BaseModel):
        description: str = Field(..., description="Item description")
        quantity: float = Field(1.0, description="Quantity")
        unit_price: float = Field(0.0, description="Unit price")
        total_price: float = Field(0.0, description="Total price")

    class Totals(BaseModel):
        subtotal: float = Field(0.0, description="Subtotal amount")
        tax_rate: float = Field(23.0, description="Tax rate percentage")
        tax_amount: float = Field(0.0, description="Tax amount")
        total: float = Field(0.0, description="Total amount")

    seller: SellerInfo = Field(default_factory=SellerInfo)
    buyer: BuyerInfo = Field(default_factory=BuyerInfo)
    items: List[LineItem] = Field(default_factory=list)
    totals: Totals = Field(default_factory=Totals)
    payment_method: str = ""
    bank_account: str = ""
    notes: str = ""


class OCRResult(BaseModel):
    """OCR extraction result"""

    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., description="OCR confidence (0-1)")
    language: str = Field(..., description="Detected language")
    engine: str = Field(..., description="OCR engine used")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationError(BaseModel):
    """Validation error details"""

    field: str = Field(..., description="Field with error")
    message: str = Field(..., description="Error message")
    value: Any = Field(None, description="Invalid value")


class ConversionMetadata(BaseModel):
    """Conversion metadata"""

    source_format: str = Field(..., description="Source file format")
    target_format: str = Field(..., description="Target file format")
    file_size: int = Field(..., description="File size in bytes")
    processing_time: float = Field(..., description="Processing time in seconds")
    ocr_confidence: Optional[float] = Field(
        None, description="OCR confidence if applicable"
    )
    pages_processed: Optional[int] = Field(
        None, description="Number of pages processed"
    )
    items_extracted: Optional[int] = Field(
        None, description="Number of items extracted"
    )
    validation_errors: List[ValidationError] = Field(default_factory=list)
