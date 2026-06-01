#!/usr/bin/env bash
set -euo pipefail

echo "WARNING: This will remove local docker volumes and data."
read -p "Continue? [y/N] " -r
if [[ "$REPLY" != "y" && "$REPLY" != "Y" ]]; then
  echo "Aborting."
  exit 1
fi

docker compose down -v
echo "Local volumes removed."
