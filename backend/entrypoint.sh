#!/bin/sh
# Bring the schema up to head, load seed data, then serve.
# Seeding is idempotent, so a restart against an existing volume is a no-op.
set -e

echo "==> Running migrations"
alembic upgrade head

echo "==> Seeding reference data"
python -m app.seed.run_seed

# Behind the nginx container, the client address uvicorn sees is the proxy's, and the
# login throttle keys on the client address. FORWARDED_ALLOW_IPS names the proxies
# whose X-Forwarded-For may be believed. The base compose file sets it to "*" and
# publishes no API port, so the proxy is the only possible caller; the dev override
# publishes :8000 and leaves it unset, so a direct caller cannot spoof the header.
if [ -n "$FORWARDED_ALLOW_IPS" ]; then
  echo "==> Starting API on :8000 (trusting X-Forwarded-For from: $FORWARDED_ALLOW_IPS)"
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
fi

echo "==> Starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
