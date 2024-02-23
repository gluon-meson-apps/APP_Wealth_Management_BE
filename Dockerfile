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

RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
RUN --mount=type=cache,target=$POETRY_CACHE_DIR --mount=type=ssh poetry install --without dev --no-root

FROM ${PYTHON_IMAGE}-slim as runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken_cache


COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}



COPY . /app

# Set the PYTHONPATH environment variable
ENV PYTHONPATH=.

RUN python -c "import tiktoken; tiktoken.encoding_for_model('gpt-4');tiktoken.encoding_for_model('gpt2')"


# Define the command to start the application
CMD cd /app/src && python app.py