#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --reload
