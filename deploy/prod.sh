#!/usr/bin/env bash
# Build prod images, restart the stack via Supervisor, reload host nginx.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.prod)

cd "$ROOT"

if [[ ! -f .env.prod ]]; then
  echo "Missing $ROOT/.env.prod — copy .env.prod.example and edit it." >&2
  exit 1
fi

if [[ ! -f /etc/supervisor/conf.d/joyce.conf ]]; then
  echo "joyce Supervisor program not installed; running install-supervisor.sh"
  "$ROOT/deploy/install-supervisor.sh"
fi

echo "==> Building images"
"${COMPOSE[@]}" build

echo "==> Restarting joyce (Supervisor)"
sudo supervisorctl restart joyce
sudo supervisorctl status joyce || true

echo "==> Reloading nginx"
if sudo nginx -t; then
  sudo systemctl reload nginx
else
  echo "nginx -t failed; stack is up but nginx was not reloaded." >&2
  exit 1
fi

echo "==> Done"
"${COMPOSE[@]}" ps
