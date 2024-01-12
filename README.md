## Setup

Requires at least Python3.9.0

## start service in local

install poetry and virtualenv, make sure poetry and virtualenv is installed, poetry related commands https://python-poetry.org/docs/cli/
```bash
pip install poetry
pip install virtualenv
```

specify python3.9
```bash
poetry env use python3.9
```
install dependencies
```bash
poetry install
```

start service
```bash
poetry run python src/app.py
```

run lint and test
```bash
poetry run make lint
poetry run make test
```

install pre-commit hook
```bash
pre-commit install
```


intent example init
```bash
poetry run python  src/nlu/llm/intent_examples.py
```