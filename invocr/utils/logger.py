"""
Logging configuration for InvOCR
Provides structured logging with file and console outputs
"""

import logging
import logging.handlers
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from loguru import logger as loguru_logger

    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False

from .config import get_settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        if hasattr(record, "levelname"):
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


class InvOCRLogger:
    """Custom logger for InvOCR with enhanced features"""

    def __init__(self, name: str = "invocr"):
        self.name = name
        self.settings = get_settings()
        self._logger = None
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger with file and console handlers"""
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(getattr(logging, self.settings.log_level))

        # Clear existing handlers
        self._logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.settings.log_level))

        if self.settings.is_development():
            console_formatter = ColoredFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            console_formatter = logging.Formatter(self.settings.log_format)

        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)

        # File handler
        log_file = self.settings.logs_dir / f"{self.name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)

        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)

        # Error file handler
        error_file = self.settings.logs_dir / f"{self.name}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"  # 5MB
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self._logger.addHandler(error_handler)

        # JSON handler for structured logging (production)
        if self.settings.is_production():
            json_file = self.settings.logs_dir / f"{self.name}_structured.log"
            json_handler = logging.handlers.RotatingFileHandler(
                json_file,
                maxBytes=20 * 1024 * 1024,  # 20MB
                backupCount=10,
                encoding="utf-8",
            )
            json_handler.setLevel(logging.INFO)
            json_handler.setFormatter(JSONFormatter())
            self._logger.addHandler(json_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._logger.critical(message, extra=kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self._logger.exception(message, extra=kwargs)

    def log_conversion(
        self, job_id: str, input_file: str, output_file: str, status: str, **metadata
    ):
        """Log conversion operation"""
        self.info(
            f"Conversion {status}: {input_file} -> {output_file}",
            job_id=job_id,
            input_file=input_file,
            output_file=output_file,
            status=status,
            **metadata,
        )

    def log_ocr_result(
        self, file_path: str, confidence: float, text_length: int, engine: str
    ):
        """Log OCR operation result"""
        self.info(
            f"OCR completed: {file_path}",
            file_path=file_path,
            confidence=confidence,
            text_length=text_length,
            engine=engine,
            operation="ocr",
        )

    def log_performance(self, operation: str, duration: float, **metrics):
        """Log performance metrics"""
        self.info(
            f"Performance: {operation} took {duration:.2f}s",
            operation=operation,
            duration=duration,
            **metrics,
        )

    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None,
    ):
        """Log API request"""
        self.info(
            f"API {method} {path} - {status_code} ({duration:.3f}s)",
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            user_id=user_id,
            operation="api_request",
        )


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record):
        import json
        from datetime import datetime

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_entry[key] = value

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


@lru_cache()
def get_logger(name: str = "invocr") -> InvOCRLogger:
    """Get cached logger instance"""
    return InvOCRLogger(name)


def setup_logging(
    level: str = None, log_file: Optional[str] = None, use_loguru: bool = False
) -> None:
    """Setup global logging configuration"""
    settings = get_settings()

    if level is None:
        level = settings.log_level

    if use_loguru and LOGURU_AVAILABLE:
        # Configure loguru
        loguru_logger.remove()  # Remove default handler

        # Console handler
        loguru_logger.add(
            sys.stdout,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>",
            colorize=True,
        )

        # File handler
        if log_file is None:
            log_file = settings.logs_dir / "invocr.log"

        loguru_logger.add(
            log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="10 MB",
            retention="30 days",
            encoding="utf-8",
        )

        # Error file
        error_file = settings.logs_dir / "invocr_errors.log"
        loguru_logger.add(
            error_file,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="5 MB",
            retention="60 days",
            encoding="utf-8",
        )

    else:
        # Use standard logging
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=settings.log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Set up file logging
        if log_file is None:
            log_file = settings.logs_dir / "invocr.log"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(settings.log_format))

        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)


def configure_external_loggers():
    """Configure external library loggers"""
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("easyocr").setLevel(logging.WARNING)
    logging.getLogger("weasyprint").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class LogContext:
    """Context manager for adding context to logs"""

    def __init__(self, logger: InvOCRLogger, **context):
        self.logger = logger
        self.context = context
        self.old_extra = {}

    def __enter__(self):
        # Store current extra context
        if hasattr(self.logger._logger, "_extra"):
            self.old_extra = self.logger._logger._extra.copy()
        else:
            self.old_extra = {}

        # Add new context
        if not hasattr(self.logger._logger, "_extra"):
            self.logger._logger._extra = {}
        self.logger._logger._extra.update(self.context)

        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old extra context
        self.logger._logger._extra = self.old_extra
