#!/bin/sh
set -e

echo "=== Running database migrations ==="
python manage.py migrate --noinput

echo "=== Starting Gunicorn ==="
exec gunicorn minghaishiyi.wsgi:application --bind 0.0.0.0:7777 --workers 4
