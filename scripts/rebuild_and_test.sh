#!/bin/bash
set -e

# Rebuild Docker images and run tests using Makefile
echo "[INFO] Rebuilding Docker images..."
make build

echo "[INFO] Running make deploy-test..."
make deploy-test
