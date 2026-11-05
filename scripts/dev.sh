#!/usr/bin/env sh
# Local dev, one command: makes .venv on first run, loads .env if present,
# builds the UI, then serves UI + API on http://localhost:8000
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements-dev.txt
(cd frontend && npm install --no-audit --no-fund && npm run build)
if [ -f .env ]; then set -a; . ./.env; set +a; fi
exec .venv/bin/python -m uvicorn src.app:app --reload --reload-dir src --port 8000
