-- Migration: Add domain generation job queue
-- Tracks async domain generation jobs initiated from the web UI.
-- The poll worker on r5 claims pending jobs, runs the pipeline, and
-- writes results back into output_json.
--
-- DSQL-compatible design:
--   - UUID primary key (no sequences)
--   - No foreign key constraints
--   - No triggers (updated_at managed by application)
--   - JSONB for output (no S3 dependency)
--   - OCC-safe claiming (no FOR UPDATE SKIP LOCKED)
--
-- Date: 2026-05-21

CREATE TABLE domain_gen_jobs (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       TEXT        NOT NULL,
    topic         TEXT        NOT NULL,
    hints         TEXT        NOT NULL DEFAULT '',
    total_terms   INTEGER     NOT NULL DEFAULT 50,
    status        TEXT        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'running', 'complete', 'failed', 'approved')),
    output_json   JSONB,
    output_path   TEXT,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_domain_gen_jobs_status     ON domain_gen_jobs (status, created_at);
CREATE INDEX idx_domain_gen_jobs_user       ON domain_gen_jobs (user_id, created_at DESC);
