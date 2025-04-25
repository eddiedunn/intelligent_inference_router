#!/bin/bash

# Variables
REMOTE_USER="eddie"
REMOTE_HOST="tela"
REMOTE_DIR="~/code/intelligent_inference_router"
PYTHONPATH="."
PYTEST_ARGS="-s router/tests/ --maxfail=5 --disable-warnings -v"

# The command to run on the remote host
REMOTE_CMD="cd $REMOTE_DIR && git pull && PYTHONPATH=$PYTHONPATH pytest $PYTEST_ARGS"

# Run the command via SSH
ssh ${REMOTE_USER}@${REMOTE_HOST} "$REMOTE_CMD"
