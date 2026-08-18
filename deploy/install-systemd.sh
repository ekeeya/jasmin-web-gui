#!/usr/bin/env bash
# One-time: render joyce.service.example → /etc/systemd/system/joyce.service
# WorkingDirectory is this checkout (e.g. /var/www/example/jasmin-web-gui).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_SRC="$ROOT/deploy/joyce.service.example"
UNIT_DST=/etc/systemd/system/joyce.service

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo -- "$0" "$@"
fi

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "Missing $UNIT_SRC" >&2
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

sed "s|@JOYCE_ROOT@|$ROOT|g" "$UNIT_SRC" > "$UNIT_DST"
systemctl daemon-reload
systemctl enable joyce.service
echo "Installed $UNIT_DST (WorkingDirectory=$ROOT)"
echo "Start/restart with:  systemctl restart joyce"
echo "Deploy with:         $ROOT/deploy/prod.sh"
