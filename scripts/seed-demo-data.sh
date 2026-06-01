#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec ./backend/scripts/seed-demo-data.sh "$@"
