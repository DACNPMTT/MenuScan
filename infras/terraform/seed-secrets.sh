#!/usr/bin/env bash
# Seed / rotate Secret Manager values from a local env file.
#
# The secret CONTAINERS are created by Terraform (secrets.tf). This script only
# adds a new VERSION (the value) to each — values never touch Terraform state or
# git. Run it once after `terraform apply`, and again whenever you rotate a key.
#
# Usage:
#   ./seed-secrets.sh ../../env/.env.local            # or any KEY=VALUE file
#   PROJECT=menuscan-500911 ./seed-secrets.sh path/to/.env
#
# The env file must define the variables listed in MAP below.

set -euo pipefail

ENV_FILE="${1:?Usage: ./seed-secrets.sh <path-to-env-file>}"
PROJECT="${PROJECT:-menuscan-500911}"

if [ ! -f "$ENV_FILE" ]; then
  echo "env file not found: $ENV_FILE" >&2
  exit 1
fi

# Load the env file into this shell (its values are only held in memory).
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# ENV_VAR_NAME -> secret-manager-secret-id
MAP=(
  "DATABASE_URL=database-url"
  "SECRET_KEY=secret-key"
  "EMAIL_SMTP_PASSWORD=email-smtp-password"
  "GOOGLE_VISION_API_KEY=google-vision-api-key"
  "GEMINI_API_KEY=gemini-api-key"
  "GEMINI_API_KEYS=gemini-api-keys"
  "ENRICH_GEMINI_API_KEYS=enrich-gemini-api-keys"
  "CHAT_GEMINI_API_KEYS=chat-gemini-api-keys"
)

for pair in "${MAP[@]}"; do
  var="${pair%%=*}"
  secret="${pair#*=}"
  value="${!var:-}"

  if [ -z "$value" ]; then
    echo "SKIP  $secret  (env var $var is empty/unset)"
    continue
  fi

  # --data-file=- reads the value from stdin so it never appears in the process
  # list or shell history. printf avoids a trailing newline.
  printf '%s' "$value" | gcloud secrets versions add "$secret" \
    --data-file=- --project="$PROJECT" >/dev/null
  echo "OK    $secret  <- \$$var"
done

echo "Done. Verify with: gcloud secrets versions list <secret> --project=$PROJECT"
