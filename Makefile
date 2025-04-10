dirs := $(shell ls | egrep 'src' | xargs)

fmt:
	ruff format $(dirs)

lint:
	ruff check $(dirs)

build-docker:
	docker build -t mcp-panther .

venv:
	uv venv

dev: venv
	. .venv/bin/activate

sync:
	uv sync