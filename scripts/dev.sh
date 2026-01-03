#!/usr/bin/env bash
set -euo pipefail

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd uv
require_cmd npm

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

BACKEND_PORT="${IBIS_BACKEND_PORT:-8000}"
FRONTEND_PORT="${IBIS_FRONTEND_PORT:-5173}"

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID:-}" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

(
  cd backend
  uv run uvicorn ibis_backend.app:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

(
  cd frontend
  npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

wait
