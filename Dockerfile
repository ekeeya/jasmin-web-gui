FROM python:3.11.8-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the current workspace into the image (no git clone).
COPY . /app

# Install Poetry using the system python (requested).
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir poetry

# Install dependencies via Poetry (skip installing the project package itself).
RUN poetry install --only main --no-root --no-ansi

# Ensure runtime server + static serving are available on PATH.
RUN python -m pip install --no-cache-dir gunicorn whitenoise


COPY ./joyce-entrypoint.sh /app/docker/joyce-entrypoint.sh

EXPOSE 8000 80

RUN chmod +x /app/docker/joyce-entrypoint.sh

ENTRYPOINT ["/bin/sh", "/app/docker/joyce-entrypoint.sh"]