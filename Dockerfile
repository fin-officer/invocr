# Multi-stage build for optimized InvOCR container
FROM python:3.11-slim as base

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-pol \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    tesseract-ocr-ita \
    poppler-utils \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN useradd --create-home --shell /bin/bash invocr
USER invocr
WORKDIR /home/invocr

# Install Poetry
RUN pip install --user poetry==1.7.1
ENV PATH="/home/invocr/.local/bin:$PATH"

# Configure Poetry
RUN poetry config virtualenvs.create false

# Copy dependency files
COPY --chown=invocr:invocr pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY --chown=invocr:invocr . .

# Install the package
RUN poetry install --no-dev --no-interaction --no-ansi

# Create directories
RUN mkdir -p logs temp uploads output

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "invocr.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

USER root
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

USER invocr
RUN poetry install --no-interaction --no-ansi

CMD ["uvicorn", "invocr.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Additional security and optimization
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

USER invocr

# Use tini as PID 1
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "invocr.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]