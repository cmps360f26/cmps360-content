#!/usr/bin/env bash

# cd /mnt/c/_cmps360-content/examples/env-setup
# chmod +x setup-env.sh
# ./setup-env.sh

# =========================================
# Safe shell settings
# =========================================
set -euo pipefail

# =========================================
# Configuration
# =========================================

ENV_NAME="py-env"
VENV_BASE="$HOME/.venvs"
ENV_PATH="$VENV_BASE/$ENV_NAME"

DEFAULT_REQ="./requirements.txt"

# =========================================
# Resolve requirements.txt path
# =========================================

REQ_PATH="${1:-$DEFAULT_REQ}"

if [ ! -f "$REQ_PATH" ]; then
    echo "ERROR: requirements.txt not found at: $REQ_PATH" >&2
    exit 1
fi

REQ_PATH="$(cd "$(dirname "$REQ_PATH")" && pwd)/$(basename "$REQ_PATH")"
echo "Using requirements file:"
echo "  $REQ_PATH"

# =========================================
# Sanity checks
# =========================================

command -v python3 >/dev/null 2>&1 || {
    echo "ERROR: python3 not found." >&2
    exit 1
}

python3 -c "import venv" >/dev/null 2>&1 || {
    echo "ERROR: Python venv module is not available." >&2
    exit 1
}

# =========================================
# Ensure base directory exists
# =========================================

mkdir -p "$VENV_BASE"

# =========================================
# Create virtual environment (idempotent)
# =========================================

if [ ! -d "$ENV_PATH" ]; then
    echo "Creating virtual environment:"
    echo "  $ENV_PATH"
    python3 -m venv "$ENV_PATH"
else
    echo "Virtual environment already exists:"
    echo "  $ENV_PATH"
fi

# =========================================
# Activate environment
# =========================================

# shellcheck disable=SC1091
source "$ENV_PATH/bin/activate"

# =========================================
# Upgrade core tooling
# =========================================

python -m pip install --upgrade pip setuptools wheel

# =========================================
# Install dependencies
# =========================================

python -m pip install -r "$REQ_PATH"

# =========================================
# Done
# =========================================

echo
echo "✅ Environment '$ENV_NAME' is ready."
echo "Activate it with:"
echo "  source $ENV_PATH/bin/activate"