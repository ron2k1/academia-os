#!/usr/bin/env bash
# AcademiaOS entrypoint -- initializes directories and starts the server.
set -euo pipefail

echo "=== AcademiaOS ==="

# Ensure persistent directories exist
mkdir -p /app/vaults /app/files /app/progress /app/config

# Copy example configs if user hasn't provided real ones
for cfg in classes models openclaw; do
    src="/app/config/${cfg}.example.json"
    # openclaw uses yaml
    if [ "$cfg" = "openclaw" ]; then
        src="/app/config/${cfg}.example.yaml"
        dst="/app/config/${cfg}.yaml"
    else
        dst="/app/config/${cfg}.json"
    fi
    if [ ! -f "$dst" ] && [ -f "$src" ]; then
        echo "  Copying $src -> $dst"
        cp "$src" "$dst"
    fi
done

# Run semester init if vaults directory is empty
if [ -z "$(ls -A /app/vaults 2>/dev/null)" ] && [ -f /app/config/classes.json ]; then
    echo "  Initializing semester structure..."
    python scripts/init_semester.py --config config/classes.json || true
fi

echo "  Starting server on ${HOST:-0.0.0.0}:${PORT:-8000}"
exec uvicorn src.server:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --log-level info \
    "$@"
