-- Migration tracking table; must run before any other migration.
-- UUID primary key (DSQL has no sequences/SERIAL).

CREATE TABLE IF NOT EXISTS schema_migrations (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    version         VARCHAR(255) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    applied_at      TIMESTAMPTZ  DEFAULT NOW(),
    checksum        VARCHAR(64),
    execution_time_ms INTEGER,
    success         BOOLEAN      DEFAULT true
);

CREATE INDEX ASYNC IF NOT EXISTS idx_schema_migrations_version    ON schema_migrations (version);
CREATE INDEX ASYNC IF NOT EXISTS idx_schema_migrations_applied_at ON schema_migrations (applied_at);
