#!/usr/bin/env sh
set -e

# Apply database migrations and seeds if starting the primary server
if [ "$1" = "daphne" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput

  echo "Ensuring languages are seeded..."
  python manage.py seed_languages --skip-existing 2>/dev/null || python manage.py seed_languages || true

  echo "Collecting static assets..."
  python manage.py collectstatic --noinput || true
fi

exec "$@"
