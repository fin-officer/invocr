# InvOCR Windows PowerShell Installation Script
# Automatically installs dependencies and sets up InvOCR on Windows

param(
    [switch]$Force,
    [switch]$Dev,
    [switch]$SkipChoco,
    [string]$InstallPath = $PWD
)

# Set colors for output
$Host.UI.RawUI.ForegroundColor = "White"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    $Host.UI.RawUI.ForegroundColor = $Color
    Write-Host $Message
    $Host.UI.RawUI.ForegroundColor = "White"
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-ChocoPackage {
    param([string]$PackageName)
    
    try {
        Write-ColorOutput "📦 Installing $PackageName..." "Yellow"
        choco install $PackageName -y --no-progress
        Write-ColorOutput "✅ $PackageName installed successfully" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "❌ Failed to install $PackageName : $_" "Red"
        return $false
    }
}

function Test-CommandExists {
    param([string]$Command)
    
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Install-Chocolatey {
    if (Test-CommandExists "choco") {
        Write-ColorOutput "✅ Chocolatey already installed" "Green"
        return $true
    }
    
    Write-ColorOutput "📦 Installing Chocolatey package manager..." "Yellow"
    
    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        
        $installScript = Invoke-WebRequest -Uri "https://community.chocolatey.org/install.ps1" -UseBasicParsing
        Invoke-Expression $installScript.Content
        
        # Refresh environment variables
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        if (Test-CommandExists "choco") {
            Write-ColorOutput "✅ Chocolatey installed successfully" "Green"
            return $true
        }
        else {
            throw "Chocolatey installation verification failed"
        }
    }
    catch {
        Write-ColorOutput "❌ Chocolatey installation failed: $_" "Red"
        return $false
    }
}

function Test-PythonVersion {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            $patch = [int]$matches[3]
            
            if ($major -ge 3 -and $minor -ge 9) {
                Write-ColorOutput "✅ Python $($matches[0]) found" "Green"
                return $true
            }
            else {
                Write-ColorOutput "❌ Python 3.9+ required, found $($matches[0])" "Red"
                return $false
            }
        }
        else {
            Write-ColorOutput "❌ Unable to determine Python version" "Red"
            return $false
        }
    }
    catch {
        Write-ColorOutput "❌ Python not found: $_" "Red"
        return $false
    }
}

function Install-Poetry {
    if (Test-CommandExists "poetry") {
        Write-ColorOutput "✅ Poetry already installed" "Green"
        return $true
    }
    
    Write-ColorOutput "📚 Installing Poetry..." "Yellow"
    
    try {
        # Install Poetry using the official installer
        (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
        
        # Add Poetry to PATH
        $poetryPath = "$env:APPDATA\Python\Scripts"
        $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        
        if ($currentPath -notlike "*$poetryPath*") {
            [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$poetryPath", "User")
            $env:PATH += ";$poetryPath"
        }
        
        # Verify installation
        Start-Sleep -Seconds 2
        if (Test-CommandExists "poetry") {
            Write-ColorOutput "✅ Poetry installed successfully" "Green"
            return $true
        }
        else {
            throw "Poetry installation verification failed"
        }
    }
    catch {
        Write-ColorOutput "❌ Poetry installation failed: $_" "Red"
        Write-ColorOutput "💡 Try manual installation: https://python-poetry.org/docs/#installation" "Yellow"
        return $false
    }
}

function Install-SystemDependencies {
    Write-ColorOutput "📦 Installing system dependencies..." "Yellow"
    
    $packages = @(
        "tesseract",
        "poppler",
        "git"
    )
    
    $successCount = 0
    foreach ($package in $packages) {
        if (Install-ChocoPackage $package) {
            $successCount++
        }
    }
    
    Write-ColorOutput "📊 Installed $successCount/$($packages.Count) packages" "Cyan"
    return $successCount -eq $packages.Count
}

function Install-TesseractLanguages {
    Write-ColorOutput "🌍 Installing Tesseract language packs..." "Yellow"
    
    $languages = @(
        "tesseract-language-pack-pol",
        "tesseract-language-pack-deu", 
        "tesseract-language-pack-fra",
        "tesseract-language-pack-spa",
        "tesseract-language-pack-ita"
    )
    
    foreach ($lang in $languages) {
        Install-ChocoPackage $lang | Out-Null
    }
}

function Install-PythonDependencies {
    Write-ColorOutput "📚 Installing Python dependencies..." "Yellow"
    
    try {
        if ($Dev) {
            poetry install --with dev
        }
        else {
            poetry install --only main
        }
        
        Write-ColorOutput "✅ Python dependencies installed" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "❌ Python dependencies installation failed: $_" "Red"
        return $false
    }
}

function New-ProjectDirectories {
    Write-ColorOutput "📁 Creating project directories..." "Yellow"
    
    $directories = @("logs", "temp", "uploads", "output", "static")
    
    foreach ($dir in $directories) {
        try {
            if (-not (Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                Write-ColorOutput "✅ Created directory: $dir" "Green"
            }
            else {
                Write-ColorOutput "ℹ️  Directory already exists: $dir" "Cyan"
            }
        }
        catch {
            Write-ColorOutput "❌ Failed to create directory $dir : $_" "Red"
        }
    }
}

function Copy-EnvironmentFile {
    Write-ColorOutput "🔧 Setting up environment configuration..." "Yellow"
    
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-ColorOutput "✅ Environment file created (.env)" "Green"
        }
        else {
            # Create basic .env file
            $envContent = @"
# InvOCR Environment Configuration
# Generated automatically for Windows

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
APP_NAME=InvOCR
VERSION=1.0.0

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Storage (Windows paths)
UPLOAD_DIR=.\uploads
OUTPUT_DIR=.\output
TEMP_DIR=.\temp
LOGS_DIR=.\logs

# File Processing
MAX_FILE_SIZE=52428800
ALLOWED_EXTENSIONS=pdf,png,jpg,jpeg,tiff,bmp,json,xml,html

# OCR Configuration
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
SECRET_KEY=change-me-in-production-windows
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
RATE_LIMIT=100/minute

# Tesseract (Windows)
TESSERACT_CMD=C:\ProgramData\chocolatey\bin\tesseract.exe
TESSDATA_PREFIX=C:\ProgramData\chocolatey\lib\tesseract\tools\tessdata

# WeasyPrint
WEASYPRINT_DPI=96
WEASYPRINT_OPTIMIZE_IMAGES=true

# Feature Flags
ENABLE_BATCH_PROCESSING=true
ENABLE_WEBHOOK_NOTIFICATIONS=false
ENABLE_EMAIL_NOTIFICATIONS=false
ENABLE_METRICS=false
ENABLE_CACHING=true
"@
            
            $envContent | Out-File -FilePath ".env" -Encoding UTF8
            Write-ColorOutput "✅ Created basic .env file" "Green"
        }
    }
    else {
        Write-ColorOutput "ℹ️  Environment file already exists" "Cyan"
    }
}

function Test-Installation {
    Write-ColorOutput "🧪 Testing installation..." "Yellow"
    
    try {
        # Test Python import
        $importTest = poetry run python -c "import invocr; print('InvOCR imported successfully')" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ InvOCR import test passed" "Green"
        }
        else {
            Write-ColorOutput "❌ InvOCR import test failed: $importTest" "Red"
            return $false
        }
        
        # Test CLI command
        $cliTest = poetry run invocr --help 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ CLI test passed" "Green"
        }
        else {
            Write-ColorOutput "❌ CLI test failed: $cliTest" "Red"
            return $false
        }
        
        return $true
    }
    catch {
        Write-ColorOutput "❌ Installation test failed: $_" "Red"
        return $false
    }
}

function Install-WindowsService {
    param([switch]$Install)
    
    if (-not $Install) {
        return
    }
    
    Write-ColorOutput "🔧 Setting up Windows Service..." "Yellow"
    
    $serviceName = "InvOCR"
    $serviceDisplayName = "InvOCR Invoice Processing Service"
    $serviceDescription = "InvOCR API service for invoice OCR and conversion"
    $servicePath = "poetry run invocr serve"
    $workingDirectory = $PWD
    
    try {
        # Check if service already exists
        $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        
        if ($existingService) {
            Write-ColorOutput "ℹ️  Service $serviceName already exists" "Cyan"
            return
        }
        
        # Create service using sc.exe (requires admin)
        if (Test-Administrator) {
            $scCommand = "sc.exe create `"$serviceName`" binPath=`"$servicePath`" DisplayName=`"$serviceDisplayName`" start=auto"
            Invoke-Expression $scCommand
            
            sc.exe description $serviceName $serviceDescription
            
            Write-ColorOutput "✅ Windows Service created: $serviceName" "Green"
            Write-ColorOutput "💡 Start service with: net start $serviceName" "Yellow"
        }
        else {
            Write-ColorOutput "⚠️  Admin privileges required for Windows Service installation" "Yellow"
            Write-ColorOutput "💡 Run PowerShell as Administrator to install service" "Yellow"
        }
    }
    catch {
        Write-ColorOutput "❌ Windows Service installation failed: $_" "Red"
    }
}

function Show-CompletionMessage {
    Write-ColorOutput "" "White"
    Write-ColorOutput "🎉 InvOCR installation completed!" "Green"
    Write-ColorOutput "=" * 50 "Green"
    Write-ColorOutput "" "White"
    
    Write-ColorOutput "📚 Quick start commands:" "Cyan"
    Write-ColorOutput "  poetry run invocr --help" "White"
    Write-ColorOutput "  poetry run invocr convert input.pdf output.json" "White"
    Write-ColorOutput "  poetry run invocr serve" "White"
    Write-ColorOutput "" "White"
    
    Write-ColorOutput "🌐 API server:" "Cyan"
    Write-ColorOutput "  poetry run invocr serve" "White"
    Write-ColorOutput "  Open: http://localhost:8000/docs" "White"
    Write-ColorOutput "" "White"
    
    Write-ColorOutput "🐳 Docker alternative:" "Cyan"
    Write-ColorOutput "  docker-compose up" "White"
    Write-ColorOutput "" "White"
    
    Write-ColorOutput "📖 Documentation:" "Cyan"
    Write-ColorOutput "  See README.md for detailed usage" "White"
    Write-ColorOutput "  API docs: http://localhost:8000/docs" "White"
    Write-ColorOutput "" "White"
    
    Write-ColorOutput "🔧 Configuration:" "Cyan"
    Write-ColorOutput "  Edit .env file to customize settings" "White"
    Write-ColorOutput "  Logs directory: .\logs\" "White"
    Write-ColorOutput "" "White"
    
    Write-ColorOutput "=" * 50 "Green"
}

function Start-DemoRun {
    $response = Read-Host "Run a quick demo? (y/n)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-ColorOutput "🚀 Running InvOCR demo..." "Yellow"
        
        try {
            poetry run invocr info
            Write-ColorOutput "✅ Demo completed successfully!" "Green"
        }
        catch {
            Write-ColorOutput "❌ Demo failed: $_" "Red"
        }
    }
}

# Main installation process
function Start-Installation {
    Write-ColorOutput "🚀 InvOCR Windows Installation Script" "Blue"
    Write-ColorOutput "======================================" "Blue"
    Write-ColorOutput "" "White"
    
    # Check execution policy
    $executionPolicy = Get-ExecutionPolicy
    if ($executionPolicy -eq "Restricted") {
        Write-ColorOutput "⚠️  PowerShell execution policy is Restricted" "Yellow"
        Write-ColorOutput "💡 Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" "Yellow"
        return
    }
    
    # Check administrator privileges
    if (Test-Administrator) {
        Write-ColorOutput "✅ Running with administrator privileges" "Green"
    }
    else {
        Write-ColorOutput "ℹ️  Running without administrator privileges" "Cyan"
        Write-ColorOutput "💡 Some features may require admin rights" "Yellow"
    }
    
    Write-ColorOutput "" "White"
    
    # Step 1: Python version check
    Write-ColorOutput "🐍 Checking Python installation..." "Yellow"
    if (-not (Test-PythonVersion)) {
        Write-ColorOutput "💡 Download Python 3.9+ from: https://python.org/downloads/" "Yellow"
        Write-ColorOutput "❌ Installation cannot continue without Python 3.9+" "Red"
        return
    }
    
    # Step 2: Install Chocolatey
    if (-not $SkipChoco) {
        Write-ColorOutput "📦 Setting up package manager..." "Yellow"
        if (-not (Install-Chocolatey)) {
            Write-ColorOutput "⚠️  Chocolatey installation failed, skipping system packages" "Yellow"
        }
    }
    
    # Step 3: Install system dependencies
    if (-not $SkipChoco -and (Test-CommandExists "choco")) {
        Install-SystemDependencies
        Install-TesseractLanguages
    }
    
    # Step 4: Install Poetry
    Write-ColorOutput "📚 Setting up Python package manager..." "Yellow"
    if (-not (Install-Poetry)) {
        Write-ColorOutput "❌ Poetry installation failed" "Red"
        return
    }
    
    # Step 5: Install Python dependencies
    Write-ColorOutput "📦 Installing Python packages..." "Yellow"
    if (-not (Install-PythonDependencies)) {
        Write-ColorOutput "❌ Python dependencies installation failed" "Red"
        return
    }
    
    # Step 6: Create directories
    New-ProjectDirectories
    
    # Step 7: Setup environment
    Copy-EnvironmentFile
    
    # Step 8: Test installation
    Write-ColorOutput "🧪 Verifying installation..." "Yellow"
    if (-not (Test-Installation)) {
        Write-ColorOutput "❌ Installation verification failed" "Red"
        return
    }
    
    # Step 9: Optional Windows Service
    if (Test-Administrator) {
        $serviceResponse = Read-Host "Install as Windows Service? (y/n)"
        if ($serviceResponse -eq 'y' -or $serviceResponse -eq 'Y') {
            Install-WindowsService -Install
        }
    }
    
    # Step 10: Show completion message
    Show-CompletionMessage
    
    # Step 11: Optional demo
    Start-DemoRun
}

# Error handling
trap {
    Write-ColorOutput "❌ An error occurred: $_" "Red"
    Write-ColorOutput "💡 Check the error message above for details" "Yellow"
    exit 1
}

# Check if script is being run directly
if ($MyInvocation.InvocationName -ne '.') {
    # Change to installation directory
    if ($InstallPath -ne $PWD) {
        Write-ColorOutput "📁 Changing to installation directory: $InstallPath" "Cyan"
        Set-Location $InstallPath
    }
    
    # Start installation
    Start-Installation
}

# Functions for manual usage
Export-ModuleMember -Function *