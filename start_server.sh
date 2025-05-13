#!/bin/bash
set -a
[ -f .env ] && source .env
set +a
uvicorn router.main:app --host 0.0.0.0 --port 8000 --env-file .env --lifespan on