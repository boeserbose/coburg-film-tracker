#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
if [ -f data/db.sqlite ]; then
  ts=$(date +"%F_%H%M%S")
  cp data/db.sqlite backups/db-${ts}.sqlite
  echo "Backed up data/db.sqlite → backups/db-${ts}.sqlite"
else
  echo "No database found at data/db.sqlite"
fi
