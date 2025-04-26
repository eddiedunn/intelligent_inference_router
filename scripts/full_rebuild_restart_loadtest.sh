#!/bin/bash
set -e

# Full rebuild, restart, and load test script for IIR
# 1. Rebuild Docker images
# 2. Restart containers
# 3. Run deploy-test (if needed)
# 4. Run remote load test
# 5. Fetch startup logs for IIR_API_KEY

# Step 1: Rebuild Docker images (try Makefile, fallback to docker-compose)
echo "[INFO] Rebuilding Docker images..."
if make build 2>/dev/null; then
  echo "[INFO] make build succeeded."
else
  echo "[WARN] make build failed, falling back to docker-compose build."
  docker-compose build
fi

# Step 2: Restart Docker containers
echo "[INFO] Restarting Docker containers..."
docker-compose down
docker-compose up -d

# Step 3: Run deploy-test (optional, comment out if not needed)
echo "[INFO] Running make deploy-test..."
make deploy-test

# Step 4: Run remote load test
echo "[INFO] Running remote load test..."
./run_remote_loadtest.sh

# Step 5: Fetch startup logs for IIR_API_KEY
echo "[INFO] Fetching startup logs for IIR_API_KEY..."
docker-compose logs --tail=50 router | grep IIR_API_KEY || echo "[WARN] No IIR_API_KEY found in logs."
