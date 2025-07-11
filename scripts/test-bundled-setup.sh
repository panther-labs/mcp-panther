#!/bin/bash
# Test script for bundled dependency setup

set -e

echo "Testing bundled MCP Python Extensions setup..."

# Source the environment configuration
if [ -f mcp_config.env ]; then
    echo "Loading environment from mcp_config.env..."
    source mcp_config.env
else
    echo "Warning: mcp_config.env not found, setting PYTHONPATH manually"
    export PYTHONPATH="${PWD}/lib:${PWD}/src"
fi

echo "PYTHONPATH is set to: $PYTHONPATH"

# Test that we can import all required dependencies
echo "Testing dependency imports..."
python3 -c "
import sys
print('Python version:', sys.version)
print('Python path:', sys.path[:3])  # Show first 3 entries

try:
    import aiohttp
    print('✓ aiohttp imported successfully')
    
    import gql
    print('✓ gql imported successfully')
    
    import mcp
    print('✓ mcp imported successfully')
    
    import fastmcp
    print('✓ fastmcp imported successfully')
    
    import click
    print('✓ click imported successfully')
    
    import uvicorn
    print('✓ uvicorn imported successfully')
    
    import starlette
    print('✓ starlette imported successfully')
    
    # Test that we can import our own modules
    from mcp_panther.panther_mcp_core.client import get_panther_gql_endpoint
    print('✓ mcp_panther modules imported successfully')
    
    print('✨ All dependencies and modules imported successfully!')
    
except ImportError as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
"

echo "✅ Bundled setup test completed successfully!" 