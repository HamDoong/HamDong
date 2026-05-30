#!/bin/sh
set -e

python - <<'PY'
import os
import socket
import time

host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))
timeout = int(os.getenv("POSTGRES_WAIT_TIMEOUT", "30"))
start = time.time()

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        if time.time() - start > timeout:
            raise
        time.sleep(1)
PY

python manage.py migrate --noinput

if [ "$APP_ENV" = "production" ]; then
    gunicorn config.wsgi:application --bind 0.0.0.0:8000
else
    python manage.py runserver 0.0.0.0:8000
fi
