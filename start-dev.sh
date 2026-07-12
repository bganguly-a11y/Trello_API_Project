#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  echo "Creating Python virtual environment..."
  if command -v python3.11 &>/dev/null; then
    PYTHON_EXEC=python3.11
  elif command -v python3.10 &>/dev/null; then
    PYTHON_EXEC=python3.10
  else
    PYTHON_EXEC=python3
  fi
  echo "Using $PYTHON_EXEC to create venv"
  $PYTHON_EXEC -m venv venv
fi

source venv/bin/activate
pip install -q -r backend/requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

cleanup() {
  trap - INT TERM EXIT
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Starting backend on http://127.0.0.1:8000"
(cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

echo "Starting frontend on http://127.0.0.1:5173"
cd frontend
npm run dev
