# Default target - show available commands
.DEFAULT_GOAL := help

# Variables
dirs := $(shell ls | egrep 'src|tests' | xargs)

# Declare phony targets (targets that don't create files)
.PHONY: help dev-deps sync venv fmt lint integration-test test mcp-dev docker

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Environment Setup
dev-deps: ## Install development dependencies (run after activating virtual environment)
	uv sync --group dev

sync: ## Synchronize dependencies with pyproject.toml
	uv sync

venv: ## Create a virtual environment using uv (run: source .venv/bin/activate after)
	uv venv

# Code Quality
fmt: ## Format code using ruff
	ruff format $(dirs)

lint: ## Lint code using ruff
	ruff check $(dirs)

# Testing
integration-test: ## Run integration tests
	FASTMCP_INTEGRATION_TEST=1 uv run pytest -s tests/panther_mcp_core/test_fastmcp_integration.py

test: ## Run all tests
	uv run pytest

# Development
mcp-dev: ## Run MCP server in development mode
	uv run fastmcp dev src/mcp_panther/server.py

# Distribution
docker: test ## Build Docker image (runs tests first)
	docker build -t mcp-panther -t mcp-panther:latest -t mcp-panther:$(shell git rev-parse --abbrev-ref HEAD | sed 's|/|-|g') .
