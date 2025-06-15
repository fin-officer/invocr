#!/bin/bash
# Development environment setup script

set -e

echo "🔧 Setting up InvOCR development environment..."

# Check if running in correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y \
        tesseract-ocr tesseract-ocr-pol tesseract-ocr-deu \
        poppler-utils libpango-1.0-0 libharfbuzz0b \
        python3-dev build-essential
elif command -v brew &> /dev/null; then
    brew install tesseract tesseract-lang poppler pango
else
    echo "⚠️  Please install system dependencies manually"
fi

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "📚 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
poetry install --with dev

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
poetry run pre-commit install

# Create development directories
echo "📁 Creating development directories..."
mkdir -p logs temp uploads output static

# Setup environment file
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file"
fi

# Run initial tests
echo "🧪 Running initial tests..."
poetry run pytest --version
poetry run pytest tests/ -v --tb=short

# Setup IDE configuration
echo "⚙️  Setting up IDE configuration..."
if [ -d ".vscode" ]; then
    echo "✅ VS Code configuration already present"
else
    echo "💡 Consider installing VS Code for better development experience"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: poetry shell"
echo "  2. Run tests: poetry run pytest"
echo "  3. Start API server: poetry run invocr serve"
echo "  4. Open http://localhost:8000/docs"
echo ""


