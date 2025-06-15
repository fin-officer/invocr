# Development and deployment automation

.PHONY: help install test lint format build docker-build docker-run deploy clean

# Default target
help:
	@echo "InvOCR Development Commands"
	@echo "=========================="
	@echo "install     - Install dependencies"
	@echo "test        - Run tests"
	@echo "lint        - Run linting"
	@echo "format      - Format code"
	@echo "build       - Build package"
	@echo "docker-build- Build Docker image"
	@echo "docker-run  - Run Docker container"
	@echo "deploy      - Deploy to production"
	@echo "clean       - Clean build artifacts"

install:
	poetry install
	poetry run pre-commit install

test:
	poetry run pytest --cov=invocr --cov-report=html

lint:
	poetry run flake8 invocr/
	poetry run mypy invocr/

format:
	poetry run black invocr/ tests/
	poetry run isort invocr/ tests/

build:
	poetry build

docker-build:
	docker build -t invocr:latest .

docker-run:
	docker-compose up -d

deploy:
	docker-compose -f docker-compose.prod.yml up -d

clean:
	rm -rf dist/ build/ *.egg-info/
	rm -rf .coverage htmlcov/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
