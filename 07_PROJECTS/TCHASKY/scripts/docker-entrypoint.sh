#!/usr/bin/env sh
set -eu

if [ -n "${DATABASE_URL:-}" ]; then
  echo "Database URL configured"
fi

if [ -n "${REDIS_URL:-}" ]; then
  echo "Redis URL configured"
fi

exec "$@"
