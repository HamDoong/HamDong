SELECT 'CREATE DATABASE identity_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'identity_db')\gexec
SELECT 'CREATE DATABASE group_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'group_db')\gexec
SELECT 'CREATE DATABASE expense_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'expense_db')\gexec
SELECT 'CREATE DATABASE settlement_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'settlement_db')\gexec
SELECT 'CREATE DATABASE media_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'media_db')\gexec
SELECT 'CREATE DATABASE notification_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'notification_db')\gexec

SELECT 'CREATE DATABASE dashboard_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dashboard_db')\gexec
