-- Migration: Add priority flag to domain_gen_jobs
-- Allows admins to mark a specific pending job for immediate processing
-- by the poll worker (which orders by priority DESC, created_at ASC).
-- Date: 2026-06-18

-- DSQL does not support ADD COLUMN with inline constraints; column is nullable,
-- treated as FALSE by application code and poll worker (NULL OR FALSE = not priority).
ALTER TABLE domain_gen_jobs ADD COLUMN IF NOT EXISTS priority BOOLEAN;

CREATE INDEX IF NOT EXISTS idx_domain_gen_jobs_priority ON domain_gen_jobs (priority DESC, created_at ASC) WHERE status = 'pending';
