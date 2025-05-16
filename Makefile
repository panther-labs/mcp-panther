dirs := $(shell ls | egrep 'src|tests' | xargs)

fmt:
	ruff format $(dirs)

lint:
	ruff check $(dirs)

docker: test
	docker build -t mcp-panther .

# Create a virtual environment using uv (https://github.com/astral-sh/uv)
# After creating, run: source .venv/bin/activate
venv:
	uv venv

# Install development dependencies (run after activating virtual environment)
dev-deps:
	uv sync --group dev

# Run tests (requires dev dependencies to be installed first)
test:
	uv run pytest

# Synchronize dependencies with pyproject.toml
sync:
	uv sync

mcp-dev:
	uv run fastmcp dev src/mcp_panther/server.py

integration-test:
	FASTMCP_INTEGRATION_TEST=1 uv run pytest -s tests/panther_mcp_core/test_fastmcp_integration.py
