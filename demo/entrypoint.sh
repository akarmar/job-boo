#!/usr/bin/env bash
# Entrypoint: loads environment, then runs the requested command.
set -euo pipefail

# ── Load environment ──────────────────────────────────────
ENV_FILE=""
if [ -f /run/secrets/env ]; then
  ENV_FILE="/run/secrets/env"
elif [ -f /root/job-boo.env ]; then
  ENV_FILE="/root/job-boo.env"
elif [ -f /opt/job-boo/.env ]; then
  ENV_FILE="/opt/job-boo/.env"
fi

if [ -n "$ENV_FILE" ]; then
  echo "Loading environment from $ENV_FILE"
  : > /tmp/.job-boo-env.sh
  while IFS= read -r line || [ -n "$line" ]; do
    # Skip comments and blanks
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    # Skip placeholder values
    [[ "$line" =~ YOUR_ ]] && continue
    # Export the variable
    export "$line" 2>/dev/null || true
    echo "export $line" >> /tmp/.job-boo-env.sh
  done < "$ENV_FILE"
fi

# ── Run the requested command ─────────────────────────────
exec "$@"
