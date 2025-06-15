"""
API routes for InvOCR
Separate route definitions for better organization
"""

import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..core.converter import create_converter
from ..utils.config import get_settings
from ..utils.logger import get_logger
from .models import (
    BatchConversionRequest,
    BatchConversionResponse,
    ConversionResponse,
    ConversionStatus,
)

logger = get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter()

# Global converter instance
converter = create_converter()

# Job storage (use Redis in production)
jobs = {}


@router.post("/convert/pdf2img", response_model=dict)
async def convert_pdf_to_images(
    file: UploadFile = File(...), format: str = Form("png"), dpi: int = Form(300)
):
    """Convert PDF to images"""

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file required")

    job_id = f"pdf2img_{hash(file.filename)}_{format}_{dpi}"

    with tempfile.TemporaryDirectory() as temp_dir:
        # Save PDF
        pdf_path = Path(temp_dir) / file.filename
        content = await file.read()

        with open(pdf_path, "wb") as f:
            f.write(content)

        # Convert to images
        output_dir = Path(settings.output_dir) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            images = converter.pdf_to_images(pdf_path, output_dir, format, dpi)

            return {
                "job_id": job_id,
                "status": "completed",
                "images": [f"/download/{job_id}/{Path(img).name}" for img in images],
                "count": len(images),
                "format": format,
                "dpi": dpi,
            }

        except Exception as e:
            logger.error(f"PDF to images conversion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/img2json", response_model=dict)
async def convert_image_to_json(
    file: UploadFile = File(...),
    languages: Optional[str] = Form(None),
    document_type: str = Form("invoice"),
    confidence_threshold: float = Form(0.3),
):
    """Convert image to JSON using OCR"""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Image file required")

    # Validate file type
    allowed_extensions = [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Unsupported image format")

    job_id = f"img2json_{hash(file.filename)}_{document_type}"

    # Parse languages
    lang_list = None
    if languages:
        lang_list = [lang.strip() for lang in languages.split(",")]

    with tempfile.TemporaryDirectory() as temp_dir:
        # Save image
        image_path = Path(temp_dir) / file.filename
        content = await file.read()

        with open(image_path, "wb") as f:
            f.write(content)

        try:
            # Create converter with specific languages
            image_converter = create_converter(lang_list)

            # Extract data using OCR
            data = image_converter.image_to_json(image_path, document_type)

            # Filter by confidence threshold
            metadata = data.get("_metadata", {})
            ocr_confidence = metadata.get("ocr_confidence", 0)

            if ocr_confidence < confidence_threshold:
                logger.warning(f"Low OCR confidence: {ocr_confidence}")

            return {
                "job_id": job_id,
                "status": "completed",
                "data": data,
                "metadata": {
                    "ocr_confidence": ocr_confidence,
                    "document_type": document_type,
                    "languages_used": lang_list or ["auto"],
                    "confidence_threshold": confidence_threshold,
                    "meets_threshold": ocr_confidence >= confidence_threshold,
                },
            }

        except Exception as e:
            logger.error(f"Image to JSON conversion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/json2xml", response_model=dict)
async def convert_json_to_xml(
    data: dict, xml_format: str = Form("eu_invoice"), validate_input: bool = Form(True)
):
    """Convert JSON data to XML format"""

    try:
        if validate_input:
            # Basic validation
            required_fields = ["document_number", "items", "totals"]
            for field in required_fields:
                if field not in data:
                    raise HTTPException(
                        status_code=400, detail=f"Missing required field: {field}"
                    )

        # Convert to XML
        xml_content = converter.json_to_xml(data, xml_format)

        if not xml_content:
            raise HTTPException(status_code=500, detail="XML conversion failed")

        job_id = f"json2xml_{hash(str(data))}_{xml_format}"

        # Save XML file
        output_dir = Path(settings.output_dir) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        xml_file = output_dir / f"invoice.xml"

        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml_content)

        return {
            "job_id": job_id,
            "status": "completed",
            "xml_format": xml_format,
            "download_url": f"/download/{job_id}/invoice.xml",
            "size": len(xml_content.encode("utf-8")),
            "preview": (
                xml_content[:500] + "..." if len(xml_content) > 500 else xml_content
            ),
        }

    except Exception as e:
        logger.error(f"JSON to XML conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/json2html", response_model=dict)
async def convert_json_to_html(
    data: dict,
    template: str = Form("modern"),
    include_css: bool = Form(True),
    responsive: bool = Form(True),
):
    """Convert JSON data to HTML format"""

    try:
        # Convert to HTML
        html_content = converter.json_to_html(data, template)

        if not html_content:
            raise HTTPException(status_code=500, detail="HTML conversion failed")

        job_id = f"json2html_{hash(str(data))}_{template}"

        # Save HTML file
        output_dir = Path(settings.output_dir) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        html_file = output_dir / f"invoice.html"

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return {
            "job_id": job_id,
            "status": "completed",
            "template": template,
            "download_url": f"/download/{job_id}/invoice.html",
            "view_url": f"/view/{job_id}/invoice.html",
            "size": len(html_content.encode("utf-8")),
            "features": {
                "responsive": responsive,
                "includes_css": include_css,
                "template_used": template,
            },
        }

    except Exception as e:
        logger.error(f"JSON to HTML conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/html2pdf", response_model=dict)
async def convert_html_to_pdf(
    html_content: str = Form(...),
    page_size: str = Form("A4"),
    margin: str = Form("20mm"),
    orientation: str = Form("portrait"),
):
    """Convert HTML content to PDF"""

    try:
        job_id = f"html2pdf_{hash(html_content)}_{page_size}"

        # Prepare PDF options
        options = {"page_size": page_size, "margin": margin, "orientation": orientation}

        # Save HTML temporarily
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as tmp_html:
            tmp_html.write(html_content)
            tmp_html.flush()

            # Convert to PDF
            output_dir = Path(settings.output_dir) / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            pdf_file = output_dir / "document.pdf"

            converter.html_to_pdf(tmp_html.name, pdf_file, options)

        # Clean up temp file
        Path(tmp_html.name).unlink()

        return {
            "job_id": job_id,
            "status": "completed",
            "download_url": f"/download/{job_id}/document.pdf",
            "options": options,
            "size": pdf_file.stat().st_size if pdf_file.exists() else 0,
        }

    except Exception as e:
        logger.error(f"HTML to PDF conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/convert", response_model=BatchConversionResponse)
async def batch_convert_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    target_format: str = Form("json"),
    languages: Optional[str] = Form(None),
    parallel_workers: int = Form(4),
):
    """Batch convert multiple files"""

    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per batch")

    job_id = f"batch_{hash(str([f.filename for f in files]))}_{target_format}"

    # Store batch job info
    jobs[job_id] = {
        "status": "processing",
        "type": "batch",
        "total_files": len(files),
        "completed_files": 0,
        "target_format": target_format,
        "created_at": "2025-06-15T12:00:00Z",
        "files": [f.filename for f in files],
    }

    # Process in background
    background_tasks.add_task(
        process_batch_files, job_id, files, target_format, languages, parallel_workers
    )

    return BatchConversionResponse(
        job_id=job_id,
        status="processing",
        message="Batch conversion started",
        total_files=len(files),
        completed_files=0,
        results_url=f"/batch/results/{job_id}",
    )


@router.get("/batch/results/{job_id}", response_model=dict)
async def get_batch_results(job_id: str):
    """Get batch conversion results"""

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")

    job = jobs[job_id]

    return {
        "job_id": job_id,
        "status": job["status"],
        "total_files": job["total_files"],
        "completed_files": job["completed_files"],
        "progress": (job["completed_files"] / job["total_files"]) * 100,
        "results": job.get("results", []),
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at"),
        "error": job.get("error"),
    }


@router.get("/view/{job_id}/{filename}")
async def view_file(job_id: str, filename: str):
    """View HTML file in browser"""

    file_path = Path(settings.output_dir) / job_id / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not filename.lower().endswith(".html"):
        raise HTTPException(status_code=400, detail="Only HTML files can be viewed")

    return FileResponse(file_path, media_type="text/html", filename=filename)


@router.delete("/jobs/{job_id}")
async def cleanup_job(job_id: str):
    """Clean up job files and data"""

    try:
        # Remove from jobs dict
        if job_id in jobs:
            del jobs[job_id]

        # Clean up files
        job_dir = Path(settings.output_dir) / job_id
        if job_dir.exists():
            import shutil

            shutil.rmtree(job_dir)

        return {"message": f"Job {job_id} cleaned up successfully"}

    except Exception as e:
        logger.error(f"Cleanup failed for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")


@router.get("/jobs", response_model=dict)
async def list_all_jobs():
    """List all jobs with their status"""

    job_list = []
    for job_id, job_data in jobs.items():
        job_list.append(
            {
                "job_id": job_id,
                "status": job_data["status"],
                "type": job_data.get("type", "single"),
                "created_at": job_data["created_at"],
                "completed_at": job_data.get("completed_at"),
                "files_count": job_data.get("total_files", 1),
            }
        )

    return {
        "jobs": job_list,
        "total_jobs": len(job_list),
        "active_jobs": len([j for j in job_list if j["status"] == "processing"]),
    }


async def process_batch_files(
    job_id: str,
    files: List[UploadFile],
    target_format: str,
    languages: Optional[str],
    parallel_workers: int,
):
    """Process batch files in background"""

    try:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        jobs[job_id]["status"] = "processing"

        # Parse languages
        lang_list = None
        if languages:
            lang_list = [lang.strip() for lang in languages.split(",")]

        # Create converter
        batch_converter = create_converter(lang_list)

        results = []
        completed = 0

        # Process files
        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            for i, file in enumerate(files):
                try:
                    # Save file temporarily
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=Path(file.filename).suffix
                    ) as tmp:
                        content = await file.read()
                        tmp.write(content)
                        tmp.flush()

                        # Convert file
                        output_dir = Path(settings.output_dir) / job_id
                        output_dir.mkdir(parents=True, exist_ok=True)
                        output_file = (
                            output_dir / f"{Path(file.filename).stem}.{target_format}"
                        )

                        result = batch_converter.convert(
                            tmp.name, output_file, "auto", target_format
                        )

                        completed += 1
                        jobs[job_id]["completed_files"] = completed

                        results.append(
                            {
                                "file": file.filename,
                                "status": (
                                    "completed" if result["success"] else "failed"
                                ),
                                "output_file": (
                                    str(output_file) if result["success"] else None
                                ),
                                "error": result.get("error"),
                                "download_url": (
                                    f"/download/{job_id}/{output_file.name}"
                                    if result["success"]
                                    else None
                                ),
                            }
                        )

                        # Clean up temp file
                        Path(tmp.name).unlink()

                except Exception as e:
                    completed += 1
                    jobs[job_id]["completed_files"] = completed

                    results.append(
                        {
                            "file": file.filename,
                            "status": "failed",
                            "error": str(e),
                            "download_url": None,
                        }
                    )

        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["results"] = results
        jobs[job_id]["completed_at"] = "2025-06-15T12:10:00Z"

    except Exception as e:
        logger.error(f"Batch processing failed for job {job_id}: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
