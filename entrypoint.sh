#!/bin/bash
set -e

.venv/bin/reflex run --env prod --backend-only --backend-port 8000 &
BACKEND_PID=$!

caddy run --config /app/Caddyfile --adapter caddyfile &
CADDY_PID=$!

wait -n
kill -TERM "$BACKEND_PID" "$CADDY_PID" 2>/dev/null || true
wait
