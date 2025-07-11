#!/bin/bash
# Bundle dependencies for dxt extension

set -e

echo "Bundling dependencies for dxt extension..."

# Use lib directory approach for better DXT compatibility
# This avoids issues with Python executable symlinks and paths
echo "Creating lib/ directory for dependency bundling..."
rm -rf lib/
mkdir -p lib/

# Export and install dependencies
echo "Exporting dependencies from lock file..."
uv export --format requirements-txt --no-dev --output-file requirements-bundle.txt

# Remove the editable install line (-e .) if it exists
sed -i.bak '/^-e \./d' requirements-bundle.txt
rm -f requirements-bundle.txt.bak

echo "Installing dependencies to lib/ directory..."
uv pip install --target lib/ --requirement requirements-bundle.txt

# Clean up temporary requirements file
rm -f requirements-bundle.txt

# Alternative Method 2: Install only runtime dependencies directly from pyproject.toml
# echo "Installing runtime dependencies from pyproject.toml..."
# uv pip install --target lib/ --no-deps $(python -c "
# import tomllib
# with open('pyproject.toml', 'rb') as f:
#     data = tomllib.load(f)
#     deps = data.get('project', {}).get('dependencies', [])
#     print(' '.join(deps))
# ")

# Alternative Method 3: Install project and dependencies (includes your source code)
# echo "Installing project and dependencies..."
# uv pip install --target lib/ .

echo "Dependencies bundled successfully in lib/"
echo "Total size:"
du -sh lib/

# Create a simple test to verify the bundling worked
echo "Testing bundled dependencies..."
PYTHONPATH="lib:src" python3 -c "
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
    print('✓ All dependencies imported successfully')
    print(f'✓ Pydantic core version: {pydantic_core_version}')
except ImportError as e:
    print(f'✗ Import error: {e}')
    exit(1)
"

echo "✓ Bundling complete and verified!"