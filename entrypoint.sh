#!/bin/bash

.venv/bin/reflex run --env prod --backend-only --backend-port 8000 &
BACKEND_PID=$!

caddy run --config /app/Caddyfile --adapter caddyfile &
CADDY_PID=$!

trap "kill -TERM $BACKEND_PID $CADDY_PID 2>/dev/null || true" SIGTERM SIGINT

wait $BACKEND_PID $CADDY_PID
exit $?
