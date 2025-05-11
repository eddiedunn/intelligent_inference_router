#!/bin/bash
set -a
[ -f .env ] && source .env
set +a

if [ -z "$IIR_API_KEY" ]; then
  echo "IIR_API_KEY is not set in .env. Please set it before running this script."
  exit 1
fi

MODEL="${MODEL:-openai/gpt-4.1}"
USER_MSG="${USER_MSG:-Hello! Who won the world series in 2020?}"
SYSTEM_MSG="${SYSTEM_MSG:-You are a helpful assistant.}"
TEMPERATURE="${TEMPERATURE:-0.7}"
STREAM="${STREAM:-false}"

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $IIR_API_KEY" \
  -d @- <<EOF
{
  "model": "$MODEL",
  "messages": [
    {"role": "system", "content": "$SYSTEM_MSG"},
    {"role": "user", "content": "$USER_MSG"}
  ],
  "temperature": $TEMPERATURE,
  "stream": $STREAM
}
EOF