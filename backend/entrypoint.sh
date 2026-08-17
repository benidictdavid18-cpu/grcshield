#!/bin/sh
# Bring the schema up to head, load seed data, then serve.
# Seeding is idempotent, so a restart against an existing volume is a no-op.
set -e

echo "==> Running migrations"
alembic upgrade head

echo "==> Seeding reference data"
python -m app.seed.run_seed

echo "==> Starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
