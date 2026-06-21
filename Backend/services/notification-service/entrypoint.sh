#!/bin/sh
set -e

python - <<'PY'
import os
import socket
import time

def wait_for(host, port, timeout=60):
    start = time.time()
    while True:
        try:
            with socket.create_connection((host, int(port)), timeout=2):
                print(f"OK: {host}:{port}")
                return
        except OSError:
            if time.time() - start > timeout:
                raise RuntimeError(f"Timeout waiting for {host}:{port}")
            time.sleep(1)

wait_for(os.getenv("POSTGRES_HOST", "postgres"), os.getenv("POSTGRES_PORT", "5432"))
wait_for(os.getenv("RABBITMQ_HOST", "rabbitmq"), os.getenv("RABBITMQ_PORT", "5672"))
if os.getenv("REDIS_HOST"):
    wait_for(os.getenv("REDIS_HOST", "redis"), os.getenv("REDIS_PORT", "6379"))
PY

if [ "${AUTO_CREATE_DB:-1}" = "1" ]; then
    echo "Ensuring database exists..."
    python - <<'PY'
import os
import psycopg
from psycopg import sql

host = os.getenv("POSTGRES_HOST", "postgres")
port = os.getenv("POSTGRES_PORT", "5432")
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
target_db = os.getenv("POSTGRES_DB")
admin_db = os.getenv("POSTGRES_ADMIN_DB", "postgres")

if not target_db:
    print("POSTGRES_DB is empty; skipping database creation")
else:
    conn = psycopg.connect(
        host=host,
        port=int(port),
        dbname=admin_db,
        user=user,
        password=password,
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
            exists = cur.fetchone() is not None
            if exists:
                print(f"Database already exists: {target_db}")
            else:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
                print(f"Database created: {target_db}")
    finally:
        conn.close()
PY
fi

if [ "${AUTO_MIGRATE:-0}" = "1" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
fi

exec "$@"
