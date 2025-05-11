#!/bin/bash
set -a
[ -f .env ] && source .env
set +a

if [ -z "$IIR_API_KEY" ]; then
  echo "IIR_API_KEY is not set in .env. Please set it before running this script."
  exit 1
fi

curl -X GET http://localhost:8000/v1/models \
  -H "Authorization: Bearer $IIR_API_KEY"
