"""
Command Line Interface for InvOCR
Provides all conversion operations via CLI
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich import print as rprint
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..core.converter import create_batch_converter, create_converter
from ..utils.config import get_settings
from ..utils.logger import get_logger

console = Console()
logger = get_logger(__name__)
settings = get_settings()


@click.group()
@click.version_option(version="1.0.0", prog_name="InvOCR")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--config", "-c", type=click.Path(), help="Custom config file")
def cli(verbose: bool, config: Optional[str]):
    """InvOCR - Invoice OCR and Conversion System"""
    if verbose:
        logger.info("Verbose mode enabled")

    if config:
        logger.info(f"Using config file: {config}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--format",
    "-f",
    default="json",
    type=click.Choice(["json", "xml", "html", "pdf"]),
    help="Output format",
)
@click.option("--languages", "-l", multiple=True, help="OCR languages (e.g., en,pl,de)")
@click.option("--template", "-t", default="modern", help="Template for HTML/XML output")
def convert(
    input_file: str, output_file: str, format: str, languages: tuple, template: str
):
    """Convert single file between formats"""

    lang_list = list(languages) if languages else None
    converter = create_converter(lang_list)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Converting {Path(input_file).name}...")

        try:
            result = converter.convert(input_file, output_file, "auto", format)

            if result["success"]:
                progress.update(task, description="✅ Conversion completed")
                console.print(
                    f"[green]✅ Successfully converted to {output_file}[/green]"
                )

                # Show metadata
                if result.get("metadata"):
                    table = Table(title="Conversion Details")
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")

                    for key, value in result["metadata"].items():
                        table.add_row(str(key), str(value))

                    console.print(table)
            else:
                progress.update(task, description="❌ Conversion failed")
                console.print(f"[red]❌ Conversion failed: {result.get('error')}[/red]")
                sys.exit(1)

        except Exception as e:
            progress.update(task, description="❌ Error occurred")
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path())
@click.option(
    "--format",
    "-f",
    default="png",
    type=click.Choice(["png", "jpg", "jpeg"]),
    help="Image format",
)
@click.option("--dpi", "-d", default=300, help="Image resolution (DPI)")
def pdf2img(pdf_file: str, output_dir: str, format: str, dpi: int):
    """Convert PDF to images (PDF → PNG/JPG)"""

    converter = create_converter()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Converting PDF to images...")

        try:
            images = converter.pdf_to_images(pdf_file, output_dir, format, dpi)

            progress.update(task, description=f"✅ Created {len(images)} images")
            console.print(
                f"[green]✅ Created {len(images)} images in {output_dir}[/green]"
            )

            for img in images:
                console.print(f"  📷 {Path(img).name}")

        except Exception as e:
            progress.update(task, description="❌ Conversion failed")
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument("image_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option("--languages", "-l", multiple=True, help="OCR languages")
@click.option(
    "--doc-type",
    "-t",
    default="invoice",
    type=click.Choice(["invoice", "receipt", "payment"]),
    help="Document type",
)
def img2json(image_file: str, output_file: str, languages: tuple, doc_type: str):
    """Convert image to JSON using OCR (IMG → JSON)"""

    lang_list = list(languages) if languages else None
    converter = create_converter(lang_list)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting text with OCR...")

        try:
            data = converter.image_to_json(image_file, doc_type)

            progress.update(task, description="💾 Saving JSON...")

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            progress.update(task, description="✅ OCR completed")
            console.print(f"[green]✅ OCR completed: {output_file}[/green]")

            # Show extraction summary
            metadata = data.get("_metadata", {})
            console.print(
                f"📊 Confidence: {metadata.get('ocr_confidence', 0) * 100:.1f}%"
            )
            console.print(
                f"🔤 Language: {metadata.get('detected_language', 'unknown')}"
            )
            console.print(f"📋 Items found: {len(data.get('items', []))}")

        except Exception as e:
            progress.update(task, description="❌ OCR failed")
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument("json_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--format", "-f", default="eu_invoice", help="XML format (eu_invoice, ubl, custom)"
)
def json2xml(json_file: str, output_file: str, format: str):
    """Convert JSON to XML (JSON → XML)"""

    converter = create_converter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Converting JSON to XML...")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            xml_content = converter.json_to_xml(data, format)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(xml_content)

            progress.update(task, description="✅ XML created")
            console.print(f"[green]✅ XML created: {output_file}[/green]")
            console.print(f"📄 Format: {format}")

        except Exception as e:
            progress.update(task, description="❌ Conversion failed")
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path())
@click.option(
    "--format",
    "-f",
    default="json",
    type=click.Choice(["json", "xml", "html", "pdf"]),
    help="Output format",
)
@click.option("--pattern", "-p", default="*", help="File pattern (e.g., *.pdf)")
@click.option("--parallel", "-j", default=4, help="Number of parallel workers")
@click.option("--languages", "-l", multiple=True, help="OCR languages")
def batch(
    input_dir: str,
    output_dir: str,
    format: str,
    pattern: str,
    parallel: int,
    languages: tuple,
):
    """Batch convert multiple files"""

    lang_list = list(languages) if languages else None
    batch_converter = create_batch_converter(lang_list)

    input_path = Path(input_dir)
    files = list(input_path.glob(pattern))

    if not files:
        console.print(f"[yellow]⚠️  No files found matching pattern: {pattern}[/yellow]")
        return

    console.print(f"📁 Found {len(files)} files to process")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing files...")

        try:
            if parallel > 1:
                results = batch_converter.convert_parallel(
                    files, output_dir, format, parallel
                )
            else:
                results = batch_converter.convert_directory(
                    input_dir, output_dir, "auto", format, pattern
                )

            # Show results summary
            successful = sum(1 for r in results if r["success"])
            failed = len(results) - successful

            progress.update(
                task, description=f"✅ Completed: {successful}/{len(results)}"
            )

            table = Table(title="Batch Conversion Results")
            table.add_column("File", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details", style="yellow")

            for result in results:
                file_name = Path(result["source_file"]).name
                status = "✅ Success" if result["success"] else "❌ Failed"
                details = result.get("error", "OK") if not result["success"] else "OK"
                table.add_row(file_name, status, details)

            console.print(table)
            console.print(f"[green]✅ Successfully processed: {successful}[/green]")

            if failed > 0:
                console.print(f"[red]❌ Failed: {failed}[/red]")

        except Exception as e:
            progress.update(task, description="❌ Batch processing failed")
            console.print(f"[red]❌ Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path())
@click.option("--languages", "-l", multiple=True, help="OCR languages")
def pipeline(input_file: str, output_dir: str, languages: tuple):
    """Full conversion pipeline: PDF → IMG → JSON → XML → HTML → PDF"""

    lang_list = list(languages) if languages else None
    converter = create_converter(lang_list)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_stem = Path(input_file).stem

    stages = [
        ("📄 PDF → Images", "pdf2img"),
        ("🔍 OCR → JSON", "img2json"),
        ("📋 JSON → XML", "json2xml"),
        ("🌐 JSON → HTML", "json2html"),
        ("📑 HTML → PDF", "html2pdf"),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        current_file = input_file
        json_data = None

        for stage_name, stage_type in stages:
            task = progress.add_task(stage_name)

            try:
                if stage_type == "pdf2img":
                    img_dir = output_path / "images"
                    img_dir.mkdir(exist_ok=True)
                    images = converter.pdf_to_images(current_file, img_dir)
                    current_file = images[0] if images else current_file

                elif stage_type == "img2json":
                    json_file = output_path / f"{file_stem}.json"
                    json_data = converter.image_to_json(current_file)
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    current_file = json_file

                elif stage_type == "json2xml":
                    xml_file = output_path / f"{file_stem}.xml"
                    xml_content = converter.json_to_xml(json_data)
                    with open(xml_file, "w", encoding="utf-8") as f:
                        f.write(xml_content)

                elif stage_type == "json2html":
                    html_file = output_path / f"{file_stem}.html"
                    html_content = converter.json_to_html(json_data)
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    current_file = html_file

                elif stage_type == "html2pdf":
                    pdf_file = output_path / f"{file_stem}_converted.pdf"
                    converter.html_to_pdf(current_file, pdf_file)

                progress.update(task, description=f"✅ {stage_name}")

            except Exception as e:
                progress.update(task, description=f"❌ {stage_name} failed")
                console.print(f"[red]❌ {stage_name} failed: {e}[/red]")
                break

        console.print(f"[green]✅ Pipeline completed! Files in: {output_dir}[/green]")


@cli.command()
@click.option("--host", default="0.0.0.0", help="API host")
@click.option("--port", default=8000, help="API port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the REST API server"""
    import uvicorn

    from ..api.main import app

    console.print(f"🚀 Starting InvOCR API server on {host}:{port}")
    console.print(f"📖 API docs: http://{host}:{port}/docs")

    uvicorn.run(
        "invocr.api.main:app", host=host, port=port, reload=reload, log_level="info"
    )


@cli.command()
@click.option("--daemon", is_flag=True, help="Run as daemon")
def worker(daemon: bool):
    """Start background worker for async processing"""
    console.print("🔧 Starting InvOCR worker...")

    if daemon:
        console.print("Running as daemon...")
        # Implement daemon mode
        pass
    else:
        console.print("Running in foreground...")
        # Implement worker loop
        pass


@cli.command()
def info():
    """Show system information and configuration"""

    table = Table(title="InvOCR System Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    # System info
    table.add_row("Version", "1.0.0")
    table.add_row("Python", sys.version.split()[0])

    # Check dependencies
    try:
        import tesseract

        table.add_row("Tesseract", "✅ Available")
    except ImportError:
        table.add_row("Tesseract", "❌ Not available")

    try:
        import easyocr

        table.add_row("EasyOCR", "✅ Available")
    except ImportError:
        table.add_row("EasyOCR", "❌ Not available")

    # Configuration
    table.add_row("Upload Dir", str(settings.upload_dir))
    table.add_row("Output Dir", str(settings.output_dir))
    table.add_row("Log Level", settings.log_level)

    console.print(table)


if __name__ == "__main__":
    cli()
