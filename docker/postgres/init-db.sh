#!/bin/bash
set -e

# Create a least-privilege application user for runtime operations.
# This script runs once when the Postgres data volume is first initialized.
# The owner (POSTGRES_USER) retains full privileges for migrations (alembic).

if [ -z "$APP_DB_PASSWORD" ]; then
    echo "WARNING: APP_DB_PASSWORD not set, skipping app user creation."
    exit 0
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create runtime user (idempotent)
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_runtime') THEN
            CREATE ROLE app_runtime WITH LOGIN PASSWORD '$APP_DB_PASSWORD';
        END IF;
    END
    \$\$;

    -- Grant connect and schema usage
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO app_runtime;
    GRANT USAGE ON SCHEMA public TO app_runtime;

    -- DML only on all current and future tables
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime;

    -- Sequences (needed for serial/identity columns)
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_runtime;
EOSQL

echo "Created least-privilege app_runtime user."
