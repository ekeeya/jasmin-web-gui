#!/usr/bin/env bash
# One-time: render joyce.conf.example → /etc/supervisor/conf.d/joyce.conf
# and point directory/command at this checkout.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONF_SRC="$ROOT/deploy/joyce.conf.example"
CONF_DST=/etc/supervisor/conf.d/joyce.conf
LOG_DIR=/var/log/joyce

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo -- "$0" "$@"
fi

if [[ ! -f "$CONF_SRC" ]]; then
  echo "Missing $CONF_SRC" >&2
  exit 1
fi
if [[ ! -f "$ROOT/.env.prod" ]]; then
  echo "Missing $ROOT/.env.prod — copy .env.prod.example first." >&2
  exit 1
fi
if [[ ! -x /usr/bin/docker ]]; then
  echo "/usr/bin/docker not found" >&2
  exit 1
fi
if ! command -v supervisorctl >/dev/null 2>&1; then
  echo "supervisorctl not found — install supervisor (e.g. apt install supervisor)" >&2
  exit 1
fi

chmod +x "$ROOT/deploy/joyce-compose.sh" "$ROOT/deploy/prod.sh" "$ROOT/deploy/install-supervisor.sh"

mkdir -p "$LOG_DIR"
sed "s|@JOYCE_ROOT@|$ROOT|g" "$CONF_SRC" > "$CONF_DST"

# Prefer Supervisor over the old systemd unit if it is still enabled.
if systemctl list-unit-files joyce.service >/dev/null 2>&1; then
  if systemctl is-enabled joyce.service >/dev/null 2>&1; then
    echo "Disabling leftover joyce.service (stack is managed by Supervisor now)"
    systemctl stop joyce.service || true
    systemctl disable joyce.service || true
  fi
fi

supervisorctl reread
supervisorctl update
echo "Installed $CONF_DST (directory=$ROOT)"
echo "Start/restart with:  supervisorctl restart joyce"
echo "Status:              supervisorctl status joyce"
echo "Deploy with:         $ROOT/deploy/prod.sh"
