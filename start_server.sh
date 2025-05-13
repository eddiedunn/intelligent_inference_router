#!/bin/bash

echo "=== RUNNING start_server.sh ==="
set -a
[ -f .env ] && source .env
set +a
uvicorn router.main:create_app --factory --host 0.0.0.0 --port 8000 --env-file .env --lifespan on