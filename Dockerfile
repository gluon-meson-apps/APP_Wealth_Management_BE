ARG PYTHON_IMAGE=python:3.9

FROM $PYTHON_IMAGE

FROM ${PYTHON_IMAGE} as builder

RUN pip install poetry==1.4.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

FROM ${PYTHON_IMAGE}-slim as runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}



COPY . /app

# Set the PYTHONPATH environment variable
ENV PYTHONPATH=.

# Define the command to start the application
CMD cd /app/src && python app.py