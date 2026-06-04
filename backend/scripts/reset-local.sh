#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/backend/docker-compose.yml"

cat <<'EOF'
WARNING: This command stops the local HamDong stack.

- It does not delete source code.
- It does not delete .env files.
- Docker volumes are removed only if you explicitly answer y.
EOF

read -r -p "Remove local Docker volumes too? [y/N] " reply

if [[ "${reply}" == "y" || "${reply}" == "Y" ]]; then
  docker compose -f "${COMPOSE_FILE}" down -v --remove-orphans
  echo "Local containers and Docker volumes removed."
else
  docker compose -f "${COMPOSE_FILE}" down --remove-orphans
  echo "Local containers stopped. Docker volumes kept."
fi
