#!/bin/bash

# Remote load test runner for FastAPI using Locust
# Runs Locust on the remote node, targeting the local FastAPI instance
# Usage: ./run_remote_loadtest.sh [locust_args]

REMOTE_USER="eddie"
REMOTE_HOST="tela"
REMOTE_DIR="~/code/intelligent_inference_router"

# Default Locust command (headless mode, 10 users, 20 total requests, can be overridden by args)
DEFAULT_LOCUST_ARGS="-f locustfile.py --host http://localhost:8000 --headless -u 10 -r 2 -t 30s"

# Allow passing custom Locust args
LOCUST_ARGS=${@:-$DEFAULT_LOCUST_ARGS}

REMOTE_CMD="cd $REMOTE_DIR && locust $LOCUST_ARGS"

ssh -t ${REMOTE_USER}@${REMOTE_HOST} "$REMOTE_CMD"
