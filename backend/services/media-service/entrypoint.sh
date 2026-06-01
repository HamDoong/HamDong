#!/bin/sh
set -e

python - <<'PY'
import os
import socket
import time

def wait_for_service(host, port, timeout=30):
    start = time.time()
    while True:
        try:
            with socket.create_connection((host, int(port)), timeout=2):
                return
        except OSError:
            if time.time() - start > timeout:
                raise
            time.sleep(1)

wait_for_service(os.getenv("POSTGRES_HOST", "postgres"), os.getenv("POSTGRES_PORT", "5432"), int(os.getenv("POSTGRES_WAIT_TIMEOUT", "30")))
wait_for_service(os.getenv("RABBITMQ_HOST", "rabbitmq"), os.getenv("RABBITMQ_PORT", "5672"), int(os.getenv("RABBITMQ_WAIT_TIMEOUT", "30")))
PY

python manage.py migrate --noinput

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

if [ "$APP_ENV" = "production" ]; then
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
else
    exec python manage.py runserver 0.0.0.0:8000
fi
