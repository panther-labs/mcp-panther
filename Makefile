dirs := $(shell ls | egrep 'src' | xargs)

fmt:
	ruff format $(dirs)

lint:
	ruff check $(dirs)