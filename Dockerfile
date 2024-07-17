FROM python:3.11.8-slim as base

RUN python -m venv /venv

FROM base as builder

RUN apt-get update && apt-get install -y build-essential

COPY requirements.txt .

RUN /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install -r requirements.txt

FROM base

COPY --from=builder /venv /venv

ENV PATH="/venv/bin:$PATH"

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app/

EXPOSE 8000

CMD ["python", "manage.py", "migrate"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]