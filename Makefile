.PHONY: test
test:
	PYTHONPATH=${PYTHONPATH}:./src:./test pytest -vv --cov=thought_agent --cov-report html --cov-report term tests/

.PHONY: lint
lint:
	ruff check ./

.PHONY: format
format:
	black src/