#!/usr/bin/env sh
# Local dev: build the UI once, then serve UI + API on http://localhost:8000
set -e
cd "$(dirname "$0")/.."
pip install -q -r requirements-dev.txt
(cd frontend && npm install --no-audit --no-fund && npm run build)
exec python -m uvicorn src.app:app --reload --port 8000
