.PHONY: test
test:
	PYTHONPATH=${PYTHONPATH}:./src:./test pytest -vv --cov=unified_search --cov-report html --cov-report term test/

.PHONY: lint
lint:
	ruff check ./

.PHONY: format
format:
	black src/