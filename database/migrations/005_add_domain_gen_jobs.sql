-- Migration: Add domain generation job queue
-- Tracks async domain generation jobs initiated from the web UI.
-- The local LAN worker polls this table for pending jobs and writes
-- results back when complete.
-- Date: 2026-05-18

CREATE TABLE domain_gen_jobs (
    id            SERIAL PRIMARY KEY,
    topic         TEXT        NOT NULL,
    hints         TEXT        NOT NULL DEFAULT '',
    total_terms   INTEGER     NOT NULL DEFAULT 50,
    status        TEXT        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'running', 'complete', 'failed')),
    output_path   TEXT,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_domain_gen_jobs_status ON domain_gen_jobs(status);
CREATE INDEX idx_domain_gen_jobs_created ON domain_gen_jobs(created_at DESC);

-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION update_domain_gen_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_domain_gen_jobs_updated_at
    BEFORE UPDATE ON domain_gen_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_domain_gen_jobs_updated_at();

-- Verify
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'domain_gen_jobs'
ORDER BY ordinal_position;
