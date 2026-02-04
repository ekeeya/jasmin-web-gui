#!/bin/sh
set -e

cd /app

# Default DB host to the Docker host's localhost (Docker Desktop).
# If you're on Linux, docker-compose adds the `host.docker.internal` mapping via `extra_hosts`.
export DB_HOST="${DB_HOST:-host.docker.internal}"

# As requested: copy from sample on every start.
if [ -f "/app/quark/datasource.py.sample" ]; then
  cp "/app/quark/datasource.py.sample" "/app/quark/datasource.py"
fi

poetry add gunicorn

cat /app/quark/datasource.py
# Wait briefly for DB connectivity (helps avoid race conditions).
# We'll attempt a lightweight DB connection check via Django.
tries="${DB_WAIT_TRIES:-20}"
sleep_s="${DB_WAIT_SLEEP_SECONDS:-2}"
while [ "$tries" -gt 0 ]; do
  if python manage.py showmigrations >/dev/null 2>&1; then
    break
  fi
  tries=$((tries - 1))
  if [ "$tries" -eq 0 ]; then
    echo "Database not ready; continuing anyway."
    break
  fi
  echo "Waiting for database... (${tries} tries left)"
  sleep "$sleep_s"
done

python manage.py migrate --noinput

# Collect static files for Gunicorn/WhiteNoise.
python manage.py collectstatic --noinput

exec gunicorn quark.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"
