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
    echo "Checking migration files..."
    python manage.py makemigrations --check --dry-run

    echo "Running migrations..."
    python manage.py migrate --noinput
    python manage.py migrate --check --noinput

    if [ "${STRICT_SCHEMA_CHECK:-1}" = "1" ]; then
        echo "Checking database schema..."
        python - <<'PY'
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from django.apps import apps
from django.db import connection

missing = []

with connection.cursor() as cursor:
    tables = set(connection.introspection.table_names(cursor))

    for model in apps.get_models():
        opts = model._meta

        if not opts.managed or opts.proxy:
            continue

        table = opts.db_table

        if table not in tables:
            missing.append(f"{table}.__table__")
            continue

        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table)
        }

        for field in opts.concrete_fields:
            if field.column not in columns:
                missing.append(f"{table}.{field.column}")

if missing:
    raise SystemExit(
        "Database schema mismatch. Missing columns/tables: "
        + ", ".join(sorted(missing))
    )

print("Database schema OK")
PY
    fi
fi

exec "$@"
