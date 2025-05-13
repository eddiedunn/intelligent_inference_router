#!/bin/bash
set -e

# Bring down the stack

echo "[IIR] Stopping and removing containers..."
docker compose down

# Rebuild all images with no cache
echo "[IIR] Building images with --no-cache..."
docker compose build --no-cache

# Start the stack up again
echo "[IIR] Starting stack..."
docker compose up -d

echo "[IIR] Stack rebuilt and started."

# Tail the logs of the router container so the user can see logs after startup
ROUTER_CONTAINER=$(docker compose ps -q router)
echo "[IIR] Tailing router logs. Press Ctrl+C to exit logs."
docker logs -f "$ROUTER_CONTAINER"
