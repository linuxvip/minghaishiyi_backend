#!/bin/sh
set -e

echo "=== Running database migrations ==="
python manage.py migrate --noinput --fake-initial

echo "=== Ensuring cache table exists ==="
python manage.py createcachetable django_cache_table 2>/dev/null || true

echo "=== Starting Gunicorn ==="
exec gunicorn minghaishiyi.wsgi:application --bind 0.0.0.0:7777 --workers 4
