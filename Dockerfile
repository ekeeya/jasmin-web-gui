FROM python:3.11.8-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      git \
      build-essential \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG JOYCE_REPO="https://github.com/ekeeya/jasmin-web-gui.git"
ARG JOYCE_REF="main"
RUN git clone --depth 1 --branch "${JOYCE_REF}" "${JOYCE_REPO}" /app

# Install Poetry using the system python (requested).
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir poetry

# Install dependencies via Poetry (skip installing the project package itself).
RUN poetry install --only main --no-root --no-ansi

# Force the datasource template used in-container to our known-good version.
COPY ./quark/datasource.py.sample /app/quark/datasource.py.sample

COPY ./joyce-entrypoint.sh /app/docker/joyce-entrypoint.sh

RUN chmod +x /app/docker/joyce-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/docker/joyce-entrypoint.sh"]