#!/bin/bash
# Usage: source hf_login.sh OR bash hf_login.sh
# Authenticates Hugging Face CLI using the HF_TOKEN environment variable if set.

if [ -n "$HF_TOKEN" ]; then
  echo "$HF_TOKEN" | huggingface-cli login --add-to-git-credential
  echo "[INFO] Hugging Face CLI authenticated from HF_TOKEN."
else
  echo "[WARN] HF_TOKEN environment variable not set. Skipping Hugging Face CLI login."
fi
