#!/bin/bash
set -e

# Make sure HF_TOKEN is set in the environment
if [ -z "$HF_TOKEN" ]; then
  echo "HF_TOKEN is not set in the environment."
  exit 1
fi

echo "Logging in to Hugging Face CLI with provided token..."
huggingface-cli login --token "$HF_TOKEN"

# Ensure ~/.huggingface exists
mkdir -p ~/.huggingface

# Copy the token to the location vLLM expects
cp ~/.cache/huggingface/token ~/.huggingface/token

echo "Hugging Face token updated and copied to ~/.huggingface/token."
