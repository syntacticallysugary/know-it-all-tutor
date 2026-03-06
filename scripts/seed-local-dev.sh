#!/usr/bin/env bash
# One-time seed script: inserts your Cognito user into the local test DB
# so the API can look you up by cognito_sub.
#
# Prerequisites:
#   sudo -u postgres psql -f scripts/sql/setup-ci-testdb.sql
#   psql postgresql://testuser:testpassword@localhost/tutor_system_test \
#        -f src/lambda_functions/migration_runner/migrations/schema_v2.sql
#
# Usage:
#   ./scripts/seed-local-dev.sh
#   ./scripts/seed-local-dev.sh  huschlej@comcast.net   (explicit email)

set -euo pipefail

EMAIL="${1:-huschlej@comcast.net}"
USER_POOL_ID="us-east-1_Bg1FA4097"
DB_URL="postgresql://testuser:testpassword@localhost:5432/tutor_system_test"

echo "==> Fetching Cognito sub for $EMAIL ..."
COGNITO_SUB=$(
  aws cognito-idp admin-get-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$EMAIL" \
    --query 'UserAttributes[?Name==`sub`].Value' \
    --output text \
    --region us-east-1
)

if [ -z "$COGNITO_SUB" ]; then
  echo "ERROR: Could not retrieve sub for $EMAIL from Cognito."
  exit 1
fi

echo "    sub = $COGNITO_SUB"
echo "==> Inserting user into local DB ..."

psql "$DB_URL" <<SQL
INSERT INTO users (cognito_sub, email, first_name, last_name)
VALUES ('$COGNITO_SUB', '$EMAIL', 'Jim', 'Huschle')
ON CONFLICT (cognito_sub) DO UPDATE
  SET email = EXCLUDED.email,
      updated_at = NOW();
SQL

echo "==> Done.  User record seeded in tutor_system_test."
echo "    You can now run ./dev.sh and log in with $EMAIL."
