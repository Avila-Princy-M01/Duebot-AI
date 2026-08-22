#!/usr/bin/env bash
set -euo pipefail
python -m pip install -e ".[dev]"
cd frontend && npm install
echo "Copy .env.example to .env and fill keys. For a local demo without Postgres:"
echo '  DATABASE_URL=sqlite+aiosqlite:///./duebot.db'
echo "Then: uvicorn backend.main:app --reload"
echo "      python scripts/seed_db.py"
echo "      cd frontend && npm run dev"
