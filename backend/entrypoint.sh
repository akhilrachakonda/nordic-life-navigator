#!/bin/sh
set -e

echo "Starting Nordic Life Navigator API..."

# Run Alembic migrations if DATABASE_URL is not SQLite
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "postgresql"; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete."
fi

# Start the application
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --limit-max-request-size 2097152
