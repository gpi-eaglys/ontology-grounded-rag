#!/usr/bin/env bash
set -euo pipefail

MODEL="google/gemma-4-12b"
CONTEXT=16384

echo "Starting LM Studio server..."
lms server start

echo "Loading $MODEL with context length $CONTEXT..."
lms load "$MODEL" --context-length "$CONTEXT"

echo "Ready. Verify with: curl http://localhost:1234/v1/models"
