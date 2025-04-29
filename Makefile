dirs := $(shell ls | egrep 'src' | xargs)

fmt:
	ruff format $(dirs)

lint:
	ruff check $(dirs)

build-docker:
	docker build -t mcp-panther .

# Create a virtual environment using uv (https://github.com/astral-sh/uv)
# After creating, run: source .venv/bin/activate
venv:
	uv venv

# Install development dependencies (run after activating virtual environment)
dev-deps:
	uv pip install -e ".[dev]"

# Run tests (requires dev dependencies to be installed first)
test:
	uv run pytest

# Synchronize dependencies with pyproject.toml
sync:
	uv sync