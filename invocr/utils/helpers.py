"""
Helper utilities for InvOCR
Common functions used across the application
"""

import hashlib
import json
import re
import tempfile
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .logger import get_logger

logger = get_logger(__name__)


def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> Path:
    """
    Ensure directory exists, create if it doesn't

    Args:
        path: Directory path
        mode: Directory permissions

    Returns:
        Path object
    """
    if isinstance(path, str):
        path = Path(path)

    path.mkdir(parents=True, exist_ok=True, mode=mode)
    return path


def clean_filename(filename: str, max_length: int = 255) -> str:
    """
    Clean filename for safe filesystem usage

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Cleaned filename
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove control characters
    filename = "".join(char for char in filename if ord(char) >= 32)

    # Normalize unicode characters
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    # Remove multiple underscores and spaces
    filename = re.sub(r"[_\s]+", "_", filename)

    # Trim and ensure not empty
    filename = filename.strip("_. ")
    if not filename:
        filename = "untitled"

    # Truncate if too long
    if len(filename) > max_length:
        name, ext = Path(filename).stem, Path(filename).suffix
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext

    return filename


def get_file_hash(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Calculate file hash

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        File hash as hex string
    """
    hash_func = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    size = float(size_bytes)

    while size >= 1024.0 and size_index < len(size_names) - 1:
        size /= 1024.0
        size_index += 1

    if size_index == 0:
        return f"{int(size)} {size_names[size_index]}"
    else:
        return f"{size:.1f} {size_names[size_index]}"


def safe_json_loads(text: str, default: Any = None) -> Any:
    """
    Safely load JSON with fallback

    Args:
        text: JSON string
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"JSON parsing failed: {e}")
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely dump object to JSON

    Args:
        obj: Object to serialize
        default: Default JSON string if serialization fails

    Returns:
        JSON string
    """
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON serialization failed: {e}")
        return default


def extract_numbers(text: str) -> List[float]:
    """
    Extract all numbers from text

    Args:
        text: Input text

    Returns:
        List of extracted numbers
    """
    # Pattern for numbers (including decimals, commas, currency)
    pattern = r"[\d\s]*[\d,]+[.,]?\d*"
    matches = re.findall(pattern, text)

    numbers = []
    for match in matches:
        # Clean and convert
        cleaned = re.sub(r"[^\d,.]", "", match)
        cleaned = cleaned.replace(",", ".")

        try:
            if "." in cleaned:
                numbers.append(float(cleaned))
            else:
                numbers.append(float(cleaned))
        except ValueError:
            continue

    return numbers


def normalize_text(text: str) -> str:
    """
    Normalize text for better processing

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)

    # Normalize line breaks
    text = re.sub(r"\r\n|\r", "\n", text)

    # Remove trailing/leading whitespace
    text = text.strip()

    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)

    return text


def create_temp_file(
    suffix: str = "", prefix: str = "invocr_", directory: Optional[Path] = None
) -> str:
    """
    Create temporary file

    Args:
        suffix: File suffix
        prefix: File prefix
        directory: Directory for temp file

    Returns:
        Temporary file path
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
    # Close file descriptor
    import os

    os.close(fd)

    return path


def cleanup_temp_files(
    directory: Union[str, Path], pattern: str = "invocr_*", max_age_hours: int = 24
) -> int:
    """
    Cleanup old temporary files

    Args:
        directory: Directory to clean
        pattern: File pattern to match
        max_age_hours: Maximum file age in hours

    Returns:
        Number of files cleaned
    """
    if isinstance(directory, str):
        directory = Path(directory)

    if not directory.exists():
        return 0

    cutoff_time = time.time() - (max_age_hours * 3600)
    cleaned_count = 0

    for file_path in directory.glob(pattern):
        try:
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                cleaned_count += 1
                logger.debug(f"Cleaned temp file: {file_path}")
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not clean file {file_path}: {e}")

    return cleaned_count


def get_file_extension(filename: str) -> str:
    """
    Get file extension in lowercase without the dot

    Args:
        filename: Filename or path

    Returns:
        File extension in lowercase without dot
    """
    return Path(filename).suffix.lstrip(".").lower()


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate file extension

    Args:
        filename: Filename to check
        allowed_extensions: List of allowed extensions

    Returns:
        True if extension is allowed
    """
    if not filename:
        return False

    extension = Path(filename).suffix.lower().lstrip(".")
    return extension in [ext.lower().lstrip(".") for ext in allowed_extensions]


def generate_job_id(prefix: str = "") -> str:
    """
    Generate unique job ID

    Args:
        prefix: Optional prefix

    Returns:
        Unique job ID
    """
    import uuid

    job_id = str(uuid.uuid4())

    if prefix:
        return f"{prefix}_{job_id}"

    return job_id


def calculate_processing_time(start_time: float) -> float:
    """
    Calculate processing time from start timestamp

    Args:
        start_time: Start timestamp

    Returns:
        Processing time in seconds
    """
    return time.time() - start_time


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying failed operations

    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier

    Returns:
        Decorator function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}")

                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff

            # All attempts failed
            logger.error(f"All {max_attempts} attempts failed")
            raise last_exception

        return wrapper

    return decorator


def batch_process(
    items: List[Any], batch_size: int = 10, processor_func=None
) -> List[Any]:
    """
    Process items in batches

    Args:
        items: Items to process
        batch_size: Size of each batch
        processor_func: Function to process each batch

    Returns:
        List of processed results
    """
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        if processor_func:
            batch_result = processor_func(batch)
            results.extend(
                batch_result if isinstance(batch_result, list) else [batch_result]
            )
        else:
            results.extend(batch)

    return results


def measure_performance(func):
    """
    Decorator to measure function performance

    Args:
        func: Function to measure

    Returns:
        Decorated function
    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time

        logger.info(
            f"Performance: {func.__name__} took {duration:.3f}s",
            function=func.__name__,
            duration=duration,
            operation="performance_measurement",
        )

        return result

    return wrapper


def sanitize_input(text: str, max_length: int = 1000000) -> str:
    """
    Sanitize user input

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        text = str(text)

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Input truncated to {max_length} characters")

    # Remove null bytes and control characters (except newlines and tabs)
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t\r")

    return text


def check_disk_space(path: Union[str, Path], required_mb: int = 100) -> bool:
    """
    Check if enough disk space is available

    Args:
        path: Path to check
        required_mb: Required space in MB

    Returns:
        True if enough space available
    """
    import shutil

    try:
        total, used, free = shutil.disk_usage(path)
        free_mb = free // (1024 * 1024)

        if free_mb < required_mb:
            logger.warning(
                f"Low disk space: {free_mb}MB available, {required_mb}MB required"
            )
            return False

        return True

    except OSError as e:
        logger.error(f"Could not check disk space: {e}")
        return False


def parse_currency_amount(text: str) -> Optional[float]:
    """
    Parse currency amount from text

    Args:
        text: Text containing currency amount

    Returns:
        Parsed amount or None
    """
    # Remove currency symbols and spaces
    cleaned = re.sub(r"[^\d,.-]", "", text)

    # Handle different decimal separators
    if "," in cleaned and "." in cleaned:
        # Assume last separator is decimal
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Check if it's likely a thousands separator
        if re.search(r",\d{3}(?!\d)", cleaned):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return None


if __name__ == "__main__":
    # Test helper functions
    print("Testing helper functions...")

    # Test filename cleaning
    dirty_filename = "Invoice #123: Company<Name> & Co.pdf"
    clean = clean_filename(dirty_filename)
    print(f"Cleaned filename: {dirty_filename} -> {clean}")

    # Test file size formatting
    sizes = [0, 512, 1024, 1048576, 1073741824]
    for size in sizes:
        print(f"{size} bytes -> {format_file_size(size)}")

    # Test number extraction
    text = "Total: $1,234.56 VAT: €234.50"
    numbers = extract_numbers(text)
    print(f"Extracted numbers: {numbers}")

    # Test currency parsing
    amounts = ["$1,234.56", "€1.234,56", "1234.56 PLN"]
    for amount in amounts:
        parsed = parse_currency_amount(amount)
        print(f"Currency: {amount} -> {parsed}")

    print("✅ Helper functions test completed")
