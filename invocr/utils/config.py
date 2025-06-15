"""
Configuration management for InvOCR
Handles environment variables and settings
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation"""

    # Application
    app_name: str = Field("InvOCR", env="APP_NAME")
    version: str = Field("1.0.0", env="VERSION")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")

    # Server
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    workers: int = Field(4, env="WORKERS")
    reload: bool = Field(False, env="RELOAD")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )

    # File Storage
    upload_dir: Path = Field(Path("./uploads"), env="UPLOAD_DIR")
    output_dir: Path = Field(Path("./output"), env="OUTPUT_DIR")
    temp_dir: Path = Field(Path("./temp"), env="TEMP_DIR")
    logs_dir: Path = Field(Path("./logs"), env="LOGS_DIR")

    # File Processing
    max_file_size: int = Field(52428800, env="MAX_FILE_SIZE")  # 50MB
    allowed_extensions: List[str] = Field(
        ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "json", "xml", "html"],
        env="ALLOWED_EXTENSIONS",
    )

    # OCR Configuration
    default_ocr_engine: str = Field("auto", env="DEFAULT_OCR_ENGINE")
    default_languages: List[str] = Field(
        ["en", "pl", "de", "fr", "es", "it"], env="DEFAULT_LANGUAGES"
    )
    ocr_confidence_threshold: float = Field(0.3, env="OCR_CONFIDENCE_THRESHOLD")
    image_dpi: int = Field(300, env="IMAGE_DPI")
    image_enhancement: bool = Field(True, env="IMAGE_ENHANCEMENT")

    # Processing
    max_pages_per_pdf: int = Field(10, env="MAX_PAGES_PER_PDF")
    parallel_workers: int = Field(4, env="PARALLEL_WORKERS")
    async_processing: bool = Field(True, env="ASYNC_PROCESSING")
    job_timeout: int = Field(300, env="JOB_TIMEOUT")  # seconds
    cleanup_interval: int = Field(3600, env="CLEANUP_INTERVAL")  # seconds

    # Security
    secret_key: str = Field("change-me-in-production", env="SECRET_KEY")
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8080"], env="CORS_ORIGINS"
    )
    rate_limit: str = Field("100/minute", env="RATE_LIMIT")

    # External Services
    database_url: Optional[str] = Field(None, env="DATABASE_URL")
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    webhook_url: Optional[str] = Field(None, env="WEBHOOK_URL")
    notification_email: Optional[str] = Field(None, env="NOTIFICATION_EMAIL")

    # Monitoring
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    metrics_enabled: bool = Field(False, env="METRICS_ENABLED")
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL")

    # Tesseract
    tesseract_cmd: str = Field("/usr/bin/tesseract", env="TESSERACT_CMD")
    tessdata_prefix: Optional[str] = Field(None, env="TESSDATA_PREFIX")

    # WeasyPrint
    weasyprint_dpi: int = Field(96, env="WEASYPRINT_DPI")
    weasyprint_optimize_images: bool = Field(True, env="WEASYPRINT_OPTIMIZE_IMAGES")

    # Feature Flags
    enable_batch_processing: bool = Field(True, env="ENABLE_BATCH_PROCESSING")
    enable_webhook_notifications: bool = Field(
        False, env="ENABLE_WEBHOOK_NOTIFICATIONS"
    )
    enable_email_notifications: bool = Field(False, env="ENABLE_EMAIL_NOTIFICATIONS")
    enable_metrics: bool = Field(False, env="ENABLE_METRICS")
    enable_caching: bool = Field(True, env="ENABLE_CACHING")

    @validator("upload_dir", "output_dir", "temp_dir", "logs_dir", pre=True)
    def ensure_path_exists(cls, v):
        """Ensure directories exist"""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v

    @validator("allowed_extensions", pre=True)
    def parse_extensions(cls, v):
        """Parse extensions from string or list"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    @validator("default_languages", pre=True)
    def parse_languages(cls, v):
        """Parse languages from string or list"""
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",")]
        return v

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @validator("default_ocr_engine")
    def validate_ocr_engine(cls, v):
        """Validate OCR engine"""
        valid_engines = ["tesseract", "easyocr", "auto"]
        if v not in valid_engines:
            raise ValueError(f"OCR engine must be one of: {valid_engines}")
        return v

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment"""
        valid_envs = ["development", "staging", "production", "testing"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"

    def get_database_config(self) -> dict:
        """Get database configuration"""
        if not self.database_url:
            return {}

        # Parse database URL
        # This is a simplified parser - use sqlalchemy.engine.url in production
        return {"url": self.database_url}

    def get_redis_config(self) -> dict:
        """Get Redis configuration"""
        if not self.redis_url:
            return {"host": "localhost", "port": 6379, "db": 0}

        # Parse Redis URL
        return {"url": self.redis_url}

    def get_cors_config(self) -> dict:
        """Get CORS configuration"""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    def get_upload_config(self) -> dict:
        """Get file upload configuration"""
        return {
            "max_size": self.max_file_size,
            "allowed_extensions": self.allowed_extensions,
            "upload_dir": str(self.upload_dir),
            "temp_dir": str(self.temp_dir),
        }

    def get_ocr_config(self) -> dict:
        """Get OCR configuration"""
        return {
            "engine": self.default_ocr_engine,
            "languages": self.default_languages,
            "confidence_threshold": self.ocr_confidence_threshold,
            "tesseract_cmd": self.tesseract_cmd,
            "tessdata_prefix": self.tessdata_prefix,
            "image_dpi": self.image_dpi,
            "image_enhancement": self.image_enhancement,
        }

    def get_processing_config(self) -> dict:
        """Get processing configuration"""
        return {
            "max_pages_per_pdf": self.max_pages_per_pdf,
            "parallel_workers": self.parallel_workers,
            "async_processing": self.async_processing,
            "job_timeout": self.job_timeout,
            "cleanup_interval": self.cleanup_interval,
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def load_config_from_file(config_file: Union[str, Path]) -> Settings:
    """Load configuration from specific file"""
    if isinstance(config_file, str):
        config_file = Path(config_file)

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    # Load settings with custom env file
    return Settings(_env_file=str(config_file))


def create_default_config(output_file: Union[str, Path] = ".env"):
    """Create default configuration file"""
    if isinstance(output_file, str):
        output_file = Path(output_file)

    default_env = """# InvOCR Configuration
# Generated automatically - modify as needed

# Application
APP_NAME=InvOCR
VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=true

# Logging
LOG_LEVEL=INFO

# Storage
UPLOAD_DIR=./uploads
OUTPUT_DIR=./output
TEMP_DIR=./temp
LOGS_DIR=./logs

# File Processing
MAX_FILE_SIZE=52428800
ALLOWED_EXTENSIONS=pdf,png,jpg,jpeg,tiff,bmp,json,xml,html

# OCR
DEFAULT_OCR_ENGINE=auto
DEFAULT_LANGUAGES=en,pl,de,fr,es,it
OCR_CONFIDENCE_THRESHOLD=0.3
IMAGE_DPI=300
IMAGE_ENHANCEMENT=true

# Processing
MAX_PAGES_PER_PDF=10
PARALLEL_WORKERS=4
ASYNC_PROCESSING=true
JOB_TIMEOUT=300
CLEANUP_INTERVAL=3600

# Security
SECRET_KEY=change-me-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
RATE_LIMIT=100/minute

# Features
ENABLE_BATCH_PROCESSING=true
ENABLE_WEBHOOK_NOTIFICATIONS=false
ENABLE_EMAIL_NOTIFICATIONS=false
ENABLE_METRICS=false
ENABLE_CACHING=true
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(default_env)

    return output_file


def validate_config() -> bool:
    """Validate current configuration"""
    try:
        settings = get_settings()

        # Check required directories
        for directory in [
            settings.upload_dir,
            settings.output_dir,
            settings.temp_dir,
            settings.logs_dir,
        ]:
            if not directory.exists():
                print(f"Warning: Directory does not exist: {directory}")

        # Check Tesseract
        if not Path(settings.tesseract_cmd).exists():
            print(f"Warning: Tesseract not found at: {settings.tesseract_cmd}")

        # Check file size limits
        if settings.max_file_size <= 0:
            print("Warning: Invalid max file size")

        return True

    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    # CLI for configuration management
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "validate":
            if validate_config():
                print("✅ Configuration is valid")
                sys.exit(0)
            else:
                print("❌ Configuration validation failed")
                sys.exit(1)

        elif command == "create":
            output_file = sys.argv[2] if len(sys.argv) > 2 else ".env"
            created_file = create_default_config(output_file)
            print(f"✅ Created configuration file: {created_file}")

        elif command == "show":
            settings = get_settings()
            print("Current configuration:")
            for field, value in settings.dict().items():
                print(f"  {field}: {value}")

        else:
            print(f"Unknown command: {command}")
            print("Available commands: validate, create, show")
            sys.exit(1)

    else:
        print("Usage: python config.py [validate|create|show]")
