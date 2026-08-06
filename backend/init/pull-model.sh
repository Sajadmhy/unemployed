#!/usr/bin/env bash
# Pulls OLLAMA_MODEL into the ollama service, printing progress, then exits.
# Ollama's /api/pull streams one JSON object per line; a plain `ollama pull`
# inside the container would work too, but the HTTP API lets this run from a
# tiny curl-only image with no ollama binary of its own.
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://ollama:11434}"
MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

echo "Waiting for Ollama at ${OLLAMA_URL}..."
until curl -sf "${OLLAMA_URL}/api/tags" > /dev/null; do
  sleep 2
done

echo "Pulling model ${MODEL}..."
last_status=""
curl -sf -N -X POST "${OLLAMA_URL}/api/pull" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"${MODEL}\"}" | while IFS= read -r line; do
    status=$(echo "$line" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || true)
    completed=$(echo "$line" | grep -o '"completed":[0-9]*' | cut -d: -f2 || true)
    total=$(echo "$line" | grep -o '"total":[0-9]*' | cut -d: -f2 || true)
    if [ -n "$total" ] && [ "$total" != "0" ] && [ -n "$completed" ]; then
      pct=$((completed * 100 / total))
      echo "${status} (${pct}%)"
    elif [ -n "$status" ] && [ "$status" != "$last_status" ]; then
      echo "$status"
      last_status="$status"
    fi
  done

# Confirm the model actually landed rather than trusting the stream reached
# "success" — a dropped connection mid-pull should fail this container.
if curl -sf "${OLLAMA_URL}/api/tags" | grep -q "\"${MODEL}\""; then
  echo "Model ${MODEL} ready."
  exit 0
else
  echo "Model ${MODEL} not found after pull." >&2
  exit 1
fi
