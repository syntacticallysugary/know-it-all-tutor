#!/usr/bin/env bash
# Local development startup script for AI Tutor System.
#
# Starts three processes:
#   1. pg-proxy (port 15432) — bridges Docker containers to host Postgres
#   2. SAM local API gateway (port 3000) — Lambda functions in Docker
#   3. Vite frontend dev server (port 5173)
#
# Why the proxy?  Lambda containers run on Docker's bridge network (172.17.x.x).
# Postgres on the host binds to 127.0.0.1 only, so containers can't reach it
# directly.  pg-proxy listens on 0.0.0.0:15432 and forwards to 127.0.0.1:5432,
# making Postgres reachable via the bridge gateway (172.17.0.1:15432).
#
# Prerequisites (one-time):
#   sudo -u postgres psql -f scripts/sql/setup-ci-testdb.sql
#   psql postgresql://testuser:testpassword@localhost/tutor_system_test \
#        -f src/lambda_functions/migration_runner/migrations/schema_v2.sql
#   ./scripts/seed-local-dev.sh          # add your Cognito user record
#   docker pull public.ecr.aws/lambda/python:3.12   # cache the Lambda image
#
# Usage:
#   ./dev.sh
#   # Then open http://localhost:5173 in your browser.
#   # API is at http://localhost:3000

set -euo pipefail
cd "$(dirname "$0")"

export AWS_DEFAULT_REGION=us-east-1

# ---------------------------------------------------------------------------
# Start the Postgres TCP proxy in the background.
# ---------------------------------------------------------------------------
echo "==> Starting pg-proxy on 0.0.0.0:15432 → 127.0.0.1:5432 ..."
python3 scripts/pg-proxy.py &
PROXY_PID=$!

# ---------------------------------------------------------------------------
# Start the Vite frontend in the background.
# Override VITE_API_BASE_URL so the frontend talks to SAM local, not prod.
# ---------------------------------------------------------------------------
echo "==> Starting Vite frontend on http://localhost:5173 ..."
(
  cd frontend
  VITE_API_BASE_URL="http://localhost:3000" \
  VITE_COGNITO_USER_POOL_ID="us-east-1_Bg1FA4097" \
  VITE_COGNITO_USER_POOL_CLIENT_ID="6d56bp4dfiu42chkdjjmln6bb9" \
  VITE_AWS_REGION="us-east-1" \
  npm run dev
) &
FRONTEND_PID=$!

# Kill everything when this script exits (Ctrl-C or error).
trap 'echo ""; echo "==> Stopping..."; kill "$PROXY_PID" "$FRONTEND_PID" 2>/dev/null; exit 0' EXIT INT TERM

# Give Vite a moment to start before printing the SAM header.
sleep 1

# ---------------------------------------------------------------------------
# Start SAM local API gateway (foreground — Ctrl-C stops everything).
#
# --warm-containers LAZY  starts containers on first request; avoids the
#                         inotify instance limit that EAGER hits.
# ---------------------------------------------------------------------------
echo "==> Starting SAM local API on http://localhost:3000 ..."
echo "    (First request to each endpoint will be slow — Lambda cold start.)"
echo ""

sam local start-api \
  --template template.yaml \
  --warm-containers LAZY \
  --port 3000
