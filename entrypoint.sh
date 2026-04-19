#!/bin/bash

.venv/bin/reflex run --env prod --backend-only --backend-port 8000 &
BACKEND_PID=$!

caddy run --config /app/Caddyfile --adapter caddyfile &
CADDY_PID=$!

trap 'kill -TERM ${BACKEND_PID} ${CADDY_PID} 2>/dev/null || true; exit 0' SIGTERM SIGINT

# Keep both processes running - if either exits, restart it
while true; do
  wait -n
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "Backend died, exiting"
    kill -TERM "${CADDY_PID}" 2>/dev/null || true
    exit 1
  fi
  if ! kill -0 "${CADDY_PID}" 2>/dev/null; then
    echo "Caddy died, exiting"
    kill -TERM "${BACKEND_PID}" 2>/dev/null || true
    exit 1
  fi
done
