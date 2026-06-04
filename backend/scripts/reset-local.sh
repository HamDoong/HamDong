#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/backend/docker-compose.yml"

echo "WARNING: This will stop the local stack and remove Docker volumes."
read -r -p "Continue? [y/N] " reply
if [[ "$reply" != "y" && "$reply" != "Y" ]]; then
  echo "Aborting."
  exit 1
fi

docker compose -f "$COMPOSE_FILE" down -v --remove-orphans
echo "Local Docker volumes removed."
