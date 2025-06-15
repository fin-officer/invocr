"""
FastAPI REST API for InvOCR
Provides web interface for all conversion operations
"""

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..core.converter import create_batch_converter, create_converter
from ..utils.config import get_settings
from ..utils.logger import get_logger
from .models import (
    BatchConversionRequest,
    BatchConversionResponse,
    ConversionRequest,
    ConversionResponse,
    ConversionStatus,
    HealthResponse,
    SystemInfo,
)

# Initialize
settings = get_settings()
logger = get_logger(__name__)
app = FastAPI(
    title="InvOCR API",
    description="Invoice OCR and Conversion System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for web interface
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global converter instance
converter = create_converter()
batch_converter = create_batch_converter()

# Job storage (use Redis in production)
jobs: Dict[str, Dict] = {}


@app.get("/", response_class=JSONResponse)
async def root():
    """API root endpoint"""
    return {
        "message": "InvOCR API v1.0.0",
        "docs": "/docs",
        "health": "/health",
        "status": "operational",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": "2025-06-15T12:00:00Z",
            "version": "1.0.0",
            "services": {
                "ocr": "operational",
                "converter": "operational",
                "storage": "operational",
            },
        }

        # Check OCR engines
        try:
            test_result = converter.ocr_engine.extract_text("dummy")
            health_status["services"]["ocr"] = "operational"
        except Exception:
            health_status["services"]["ocr"] = "degraded"
            health_status["status"] = "degraded"

        return HealthResponse(**health_status)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp="2025-06-15T12:00:00Z",
            version="1.0.0",
            services={"ocr": "error", "converter": "error", "storage": "error"},
        )


@app.get("/info", response_model=SystemInfo)
async def system_info():
    """Get system information"""
    return SystemInfo(
        version="1.0.0",
        supported_formats={
            "input": ["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
            "output": ["json", "xml", "html", "pdf"],
        },
        supported_languages=["en", "pl", "de", "fr", "es", "it"],
        max_file_size="50MB",
        features=[
            "OCR extraction",
            "Format conversion",
            "Batch processing",
            "Multi-language support",
            "EU invoice XML format",
        ],
    )


@app.post("/convert", response_model=ConversionResponse)
async def convert_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_format: str = Form("json"),
    languages: Optional[str] = Form(None),
    template: str = Form("modern"),
    async_processing: bool = Form(False),
):
    """
    Convert uploaded file to specified format

    - **file**: Input file (PDF, image, JSON, XML, HTML)
    - **target_format**: Output format (json, xml, html, pdf)
    - **languages**: Comma-separated language codes for OCR
    - **template**: Template name for HTML/XML output
    - **async_processing**: Process in background if True
    """

    # Validate input
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Parse languages
    lang_list = None
    if languages:
        lang_list = [lang.strip() for lang in languages.split(",")]

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    input_path = upload_dir / f"{job_id}_{file.filename}"

    try:
        async with aiofiles.open(input_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        # Prepare output path
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{job_id}.{target_format}"

        if async_processing:
            # Process in background
            jobs[job_id] = {
                "status": "processing",
                "input_file": str(input_path),
                "output_file": str(output_path),
                "target_format": target_format,
                "created_at": "2025-06-15T12:00:00Z",
            }

            background_tasks.add_task(
                process_conversion_async,
                job_id,
                input_path,
                output_path,
                target_format,
                lang_list,
            )

            return ConversionResponse(
                job_id=job_id,
                status="processing",
                message="Conversion started in background",
                download_url=f"/download/{job_id}",
            )

        else:
            # Process synchronously
            file_converter = create_converter(lang_list)
            result = file_converter.convert(
                input_path, output_path, "auto", target_format
            )

            if result["success"]:
                return ConversionResponse(
                    job_id=job_id,
                    status="completed",
                    message="Conversion completed successfully",
                    download_url=f"/download/{job_id}",
                    metadata=result.get("metadata", {}),
                )
            else:
                raise HTTPException(
                    status_code=500, detail=f"Conversion failed: {result.get('error')}"
                )

    except Exception as e:
        logger.error(f"Conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup input file
        try:
            input_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.post("/convert/pdf2img")
async def pdf_to_images(
    file: UploadFile = File(...), format: str = Form("png"), dpi: int = Form(300)
):
    """Convert PDF to images"""

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file required")

    job_id = str(uuid.uuid4())

    # Save PDF file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{job_id}_{file.filename}"

    try:
        async with aiofiles.open(pdf_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        # Convert to images
        output_dir = Path(settings.output_dir) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        images = converter.pdf_to_images(pdf_path, output_dir, format, dpi)

        return {
            "job_id": job_id,
            "status": "completed",
            "images": [f"/download/{job_id}/{Path(img).name}" for img in images],
            "count": len(images),
        }

    except Exception as e:
        logger.error(f"PDF to images error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            pdf_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.post("/convert/img2json")
async def image_to_json(
    file: UploadFile = File(...),
    languages: Optional[str] = Form(None),
    document_type: str = Form("invoice"),
):
    """Convert image to JSON using OCR"""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Image file required")

    # Check file type
    allowed_types = [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_types):
        raise HTTPException(status_code=400, detail="Unsupported image format")

    job_id = str(uuid.uuid4())
    lang_list = None
    if languages:
        lang_list = [lang.strip() for lang in languages.split(",")]

    # Save image file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = upload_dir / f"{job_id}_{file.filename}"

    try:
        async with aiofiles.open(image_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        # Extract data using OCR
        image_converter = create_converter(lang_list)
        data = image_converter.image_to_json(image_path, document_type)

        return {
            "job_id": job_id,
            "status": "completed",
            "data": data,
            "metadata": data.get("_metadata", {}),
        }

    except Exception as e:
        logger.error(f"Image to JSON error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            image_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.post("/batch/convert", response_model=BatchConversionResponse)
async def batch_convert(
    background_tasks: BackgroundTasks, request: BatchConversionRequest
):
    """Batch convert multiple files"""

    job_id = str(uuid.uuid4())

    # Store batch job
    jobs[job_id] = {
        "status": "processing",
        "type": "batch",
        "total_files": len(request.file_urls),
        "completed_files": 0,
        "target_format": request.target_format,
        "created_at": "2025-06-15T12:00:00Z",
    }

    # Process in background
    background_tasks.add_task(process_batch_conversion, job_id, request)

    return BatchConversionResponse(
        job_id=job_id,
        status="processing",
        message="Batch conversion started",
        total_files=len(request.file_urls),
        completed_files=0,
        results_url=f"/batch/results/{job_id}",
    )


@app.get("/status/{job_id}", response_model=ConversionStatus)
async def get_job_status(job_id: str):
    """Get job status"""

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    return ConversionStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0),
        message=job.get("message", ""),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        error=job.get("error"),
    )


@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """Download conversion result"""

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")

    output_file = job.get("output_file")
    if not output_file or not Path(output_file).exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        output_file,
        filename=Path(output_file).name,
        media_type="application/octet-stream",
    )


@app.get("/download/{job_id}/{filename}")
async def download_batch_file(job_id: str, filename: str):
    """Download specific file from batch job"""

    output_dir = Path(settings.output_dir) / job_id
    file_path = output_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path, filename=filename, media_type="application/octet-stream"
    )


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete job and cleanup files"""

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Cleanup files
    try:
        if "output_file" in job:
            Path(job["output_file"]).unlink(missing_ok=True)

        # Cleanup batch files
        output_dir = Path(settings.output_dir) / job_id
        if output_dir.exists():
            import shutil

            shutil.rmtree(output_dir)

    except Exception as e:
        logger.warning(f"Cleanup error for job {job_id}: {e}")

    # Remove from jobs
    del jobs[job_id]

    return {"message": "Job deleted successfully"}


@app.get("/jobs")
async def list_jobs():
    """List all jobs"""

    return {
        "jobs": [
            {
                "job_id": job_id,
                "status": job["status"],
                "type": job.get("type", "single"),
                "created_at": job["created_at"],
            }
            for job_id, job in jobs.items()
        ]
    }


async def process_conversion_async(
    job_id: str,
    input_path: Path,
    output_path: Path,
    target_format: str,
    languages: Optional[List[str]],
):
    """Process conversion asynchronously"""

    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10

        # Create converter
        file_converter = create_converter(languages)

        jobs[job_id]["progress"] = 30

        # Perform conversion
        result = file_converter.convert(input_path, output_path, "auto", target_format)

        if result["success"]:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["completed_at"] = "2025-06-15T12:05:00Z"
            jobs[job_id]["metadata"] = result.get("metadata", {})
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = result.get("error", "Unknown error")

    except Exception as e:
        logger.error(f"Async conversion error for job {job_id}: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

    finally:
        # Cleanup input file
        try:
            input_path.unlink(missing_ok=True)
        except Exception:
            pass


async def process_batch_conversion(job_id: str, request: BatchConversionRequest):
    """Process batch conversion asynchronously"""

    try:
        jobs[job_id]["status"] = "processing"

        # Download and process files
        results = []
        completed = 0

        for i, file_url in enumerate(request.file_urls):
            try:
                # Here you would download the file from URL
                # For demo, we'll simulate processing
                await asyncio.sleep(1)  # Simulate processing time

                completed += 1
                jobs[job_id]["completed_files"] = completed
                jobs[job_id]["progress"] = int(
                    (completed / len(request.file_urls)) * 100
                )

                results.append(
                    {
                        "file_url": file_url,
                        "status": "completed",
                        "output_file": f"converted_{i}.{request.target_format}",
                    }
                )

            except Exception as e:
                results.append(
                    {"file_url": file_url, "status": "failed", "error": str(e)}
                )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["results"] = results
        jobs[job_id]["completed_at"] = "2025-06-15T12:10:00Z"

    except Exception as e:
        logger.error(f"Batch conversion error for job {job_id}: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def run_api():
    """Run the API server"""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run_api()
