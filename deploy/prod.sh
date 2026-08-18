#!/usr/bin/env bash
# Build prod images, restart the stack via systemd, reload host nginx.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.prod)

cd "$ROOT"

if [[ ! -f .env.prod ]]; then
  echo "Missing $ROOT/.env.prod — copy .env.prod.example and edit it." >&2
  exit 1
fi

if [[ ! -f /etc/systemd/system/joyce.service ]]; then
  echo "joyce.service not installed; running install-systemd.sh"
  "$ROOT/deploy/install-systemd.sh"
fi

echo "==> Building images"
"${COMPOSE[@]}" build

echo "==> Restarting joyce.service"
sudo systemctl restart joyce.service
sudo systemctl --no-pager --full status joyce.service || true

echo "==> Reloading nginx"
if sudo nginx -t; then
  sudo systemctl reload nginx
else
  echo "nginx -t failed; stack is up but nginx was not reloaded." >&2
  exit 1
fi

echo "==> Done"
"${COMPOSE[@]}" ps
