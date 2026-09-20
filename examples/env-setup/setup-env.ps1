# Run using .\setup-env.ps1 -ReqPath "C:\path\to\requirements.txt" or leave out to use file in the current path
param (
    [string]$ReqPath
)

# ================================
# Configuration
# ================================

$ENV_NAME  = "py-env"
$VENV_BASE = "$env:USERPROFILE\.venvs"
$ENV_PATH  = "$VENV_BASE\$ENV_NAME"

# ================================
# Resolve requirements.txt path
# ================================

if (-not $ReqPath) {
    # Default to current folder
    $ReqPath = ".\requirements.txt"
}

if (-not (Test-Path $ReqPath)) {
    Write-Error "❌ requirements.txt not found at: $ReqPath"
    exit 1
}

$ReqPath = Resolve-Path $ReqPath
Write-Host "📦 Using requirements file: $ReqPath"

# ================================
# Ensure base directory exists
# ================================

if (-not (Test-Path $VENV_BASE)) {
    New-Item -ItemType Directory -Path $VENV_BASE | Out-Null
}

# ================================
# Create virtual environment
# ================================

if (-not (Test-Path $ENV_PATH)) {
    python -m venv $ENV_PATH
}

# ================================
# Activate environment
# ================================

& "$ENV_PATH\Scripts\Activate.ps1"

# ================================
# Install dependencies
# ================================

python -m pip install --upgrade pip
pip install -r $ReqPath

Write-Host "✅ Environment '$ENV_NAME' is ready."