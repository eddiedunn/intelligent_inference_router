#!/bin/bash

# Variables
REMOTE_USER="eddie"
REMOTE_HOST="tela"
REMOTE_DIR="~/code/intelligent_inference_router"

# Step 1: Pull latest code and install dependencies
ssh ${REMOTE_USER}@${REMOTE_HOST} "cd $REMOTE_DIR && git pull && pip install -r requirements.txt"

# Step 2: Generate a new API key and update .env/client.env (seamless, preserves comments, backs up old keys)
ssh ${REMOTE_USER}@${REMOTE_HOST} "cd $REMOTE_DIR && python3 generate_api_key.py --set-server-env --set-client-env"

# Step 3: Restart the app (Docker Compose example)
ssh ${REMOTE_USER}@${REMOTE_HOST} "cd $REMOTE_DIR && docker-compose restart"

# The command to run on the remote host
REMOTE_CMD="cd $REMOTE_DIR && docker-compose up -d"

# Run the command via SSH
ssh ${REMOTE_USER}@${REMOTE_HOST} "$REMOTE_CMD"
