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
PY

if [ "${AUTO_CREATE_DB:-1}" = "1" ]; then
    echo "Ensuring database exists..."
    python - <<'PY'
import os
import time
import psycopg
from psycopg import sql

host = os.environ.get("POSTGRES_HOST", "postgres")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
user = os.environ.get("POSTGRES_USER", "postgres")
password = os.environ.get("POSTGRES_PASSWORD", "postgres")
db_name = os.environ.get("POSTGRES_DB", "wallet_db")

for attempt in range(30):
    try:
        with psycopg.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port,
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                exists = cur.fetchone() is not None

                if not exists:
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                    print(f"Created database: {db_name}")
                else:
                    print(f"Database already exists: {db_name}")

        break
    except Exception as exc:
        if attempt == 29:
            raise
        print(f"Waiting for postgres to create/check database {db_name}: {exc}")
        time.sleep(1)
PY
fi

python manage.py migrate --noinput

exec "$@"