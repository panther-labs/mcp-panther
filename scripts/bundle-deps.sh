#!/bin/bash
# Bundle dependencies for dxt extension using complete virtual environment

set -e

echo "Creating complete virtual environment for DXT extension..."

# Create server directory if it doesn't exist
mkdir -p server

# Remove existing venv and create fresh one
echo "Creating fresh virtual environment in server/venv/..."
rm -rf server/venv/
python3 -m venv --copies server/venv/

# Activate the virtual environment
source server/venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Export dependencies from uv lock file
echo "Exporting dependencies from lock file..."
uv export --format requirements-txt --no-dev --output-file requirements-bundle.txt

# Remove the editable install line (-e .) if it exists
sed -i.bak '/^-e \./d' requirements-bundle.txt
rm -f requirements-bundle.txt.bak

# Install all dependencies into the virtual environment
echo "Installing dependencies into virtual environment..."
pip install --requirement requirements-bundle.txt

# Clean up temporary requirements file
rm -f requirements-bundle.txt

# Set proper permissions for Python executables in the virtual environment
echo "Setting executable permissions..."
chmod +x server/venv/bin/python*
chmod +x server/venv/bin/pip*

echo "Virtual environment created successfully in server/venv/"
echo "Total size:"
du -sh server/venv/

# Test the virtual environment
echo "Testing virtual environment..."
source server/venv/bin/activate
python3 -c "
try:
    import aiohttp
    import gql
    import mcp
    import click
    import uvicorn
    import starlette
    import fastmcp
    import pydantic
    from pydantic_core import __version__ as pydantic_core_version
    print('✓ All dependencies imported successfully in venv')
    print(f'✓ Pydantic core version: {pydantic_core_version}')
except ImportError as e:
    print(f'✗ Import error: {e}')
    exit(1)
"

echo "✓ Virtual environment setup complete and verified!"