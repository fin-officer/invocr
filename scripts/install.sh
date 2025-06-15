#!/bin/bash
# InvOCR Installation Script for Linux/macOS
# Automatically installs dependencies and sets up the environment

set -e

echo "🚀 InvOCR Installation Script"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        log_success "$1 is installed"
        return 0
    else
        log_warning "$1 is not installed"
        return 1
    fi
}

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    log_info "Detected Linux OS"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    log_info "Detected macOS"
else
    log_error "Unsupported OS: $OSTYPE"
    exit 1
fi

# Check Python version
log_info "Checking Python installation..."
if ! check_command python3; then
    log_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    log_success "Python $PYTHON_VERSION (meets requirement >= $REQUIRED_VERSION)"
else
    log_error "Python $PYTHON_VERSION found, but >= $REQUIRED_VERSION required"
    exit 1
fi

# Install system dependencies
log_info "Installing system dependencies..."

if [[ "$OS" == "linux" ]]; then
    # Detect Linux distribution
    if command -v apt &> /dev/null; then
        log_info "Using apt package manager (Debian/Ubuntu)"

        sudo apt update
        sudo apt install -y \
            tesseract-ocr \
            tesseract-ocr-eng \
            tesseract-ocr-pol \
            tesseract-ocr-deu \
            tesseract-ocr-fra \
            tesseract-ocr-spa \
            tesseract-ocr-ita \
            poppler-utils \
            libpango-1.0-0 \
            libharfbuzz0b \
            libpangoft2-1.0-0 \
            libffi-dev \
            python3-dev \
            python3-pip \
            python3-venv \
            build-essential \
            libjpeg-dev \
            libpng-dev \
            libgl1-mesa-glx \
            libglib2.0-0 \
            libsm6 \
            libxext6 \
            libxrender-dev \
            libgomp1

    elif command -v yum &> /dev/null; then
        log_info "Using yum package manager (CentOS/RHEL)"

        sudo yum install -y \
            tesseract \
            tesseract-langpack-eng \
            tesseract-langpack-pol \
            tesseract-langpack-deu \
            tesseract-langpack-fra \
            tesseract-langpack-spa \
            tesseract-langpack-ita \
            poppler-utils \
            pango-devel \
            python3-devel \
            python3-pip \
            gcc \
            gcc-c++ \
            make

    elif command -v pacman &> /dev/null; then
        log_info "Using pacman package manager (Arch Linux)"

        sudo pacman -S --noconfirm \
            tesseract \
            tesseract-data-eng \
            tesseract-data-pol \
            tesseract-data-deu \
            tesseract-data-fra \
            tesseract-data-spa \
            tesseract-data-ita \
            poppler \
            pango \
            python \
            python-pip \
            base-devel
    else
        log_warning "Unknown package manager. Manual installation may be required."
    fi

elif [[ "$OS" == "macos" ]]; then
    log_info "Installing dependencies via Homebrew..."

    if ! check_command brew; then
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    brew install \
        tesseract \
        tesseract-lang \
        poppler \
        pango \
        python@3.11
fi

log_success "System dependencies installed"

# Check if Poetry is installed
log_info "Checking Poetry installation..."
if ! check_command poetry; then
    log_info "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -

    # Add Poetry to PATH
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

    if check_command poetry; then
        log_success "Poetry installed successfully"
    else
        log_error "Poetry installation failed"
        exit 1
    fi
else
    log_success "Poetry is already installed"
fi

# Install Python dependencies
log_info "Installing Python dependencies..."
poetry install

log_success "Python dependencies installed"

# Create directories
log_info "Creating project directories..."
mkdir -p logs temp uploads output
log_success "Directories created"

# Set up environment file
log_info "Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    log_success "Environment file created (.env)"
else
    log_info "Environment file already exists"
fi

# Test installation
log_info "Testing installation..."
if poetry run python -c "import invocr; print('InvOCR imported successfully')"; then
    log_success "Installation test passed"
else
    log_error "Installation test failed"
    exit 1
fi

# Install as system command (optional)
read -p "Install invocr as system command? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Installing system command..."

    # Create symlink or install globally
    INSTALL_DIR="/usr/local/bin"
    if [ -w "$INSTALL_DIR" ]; then
        poetry build
        pip3 install --user dist/*.whl
        log_success "InvOCR installed as system command"
    else
        log_warning "No write permission to $INSTALL_DIR, skipping system install"
    fi
fi

# Final setup
echo
echo "=============================="
log_success "🎉 InvOCR installation completed!"
echo
echo "📚 Quick start:"
echo "  poetry run invocr --help"
echo "  poetry run invocr convert input.pdf output.json"
echo "  poetry run invocr serve  # Start API server"
echo
echo "🌐 API server:"
echo "  poetry run invocr serve"
echo "  Open http://localhost:8000/docs"
echo
echo "🐳 Docker:"
echo "  docker-compose up"
echo
echo "📖 Documentation:"
echo "  See README.md for detailed usage"
echo "=============================="

# Optional: Run demo
read -p "Run a quick demo? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Running demo..."
    poetry run invocr info
fi

log_success "Installation script completed!"