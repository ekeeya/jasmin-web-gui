#!/usr/bin/env bash
# Run the prod Compose stack in the foreground for Supervisor.
# On SIGTERM/SIGINT (supervisorctl stop), run `compose down` like systemd ExecStop.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env.prod)

cd "$ROOT"

if [[ ! -f .env.prod ]]; then
  echo "Missing $ROOT/.env.prod" >&2
  exit 1
fi

cleanup() {
  echo "joyce-compose: stopping stack (compose down)..."
  "${COMPOSE[@]}" down || true
  exit 0
}

trap cleanup TERM INT

"${COMPOSE[@]}" up --abort-on-container-exit --remove-orphans &
pid=$!
wait "$pid"
status=$?
trap - TERM INT
"${COMPOSE[@]}" down || true
exit "$status"
