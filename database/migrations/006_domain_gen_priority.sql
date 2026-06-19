-- Migration: Add priority flag to domain_gen_jobs
-- Allows admins to mark a specific pending job for immediate processing
-- by the poll worker (which orders by priority DESC, created_at ASC).
-- Date: 2026-06-18

ALTER TABLE domain_gen_jobs ADD COLUMN IF NOT EXISTS priority BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_domain_gen_jobs_priority ON domain_gen_jobs (priority DESC, created_at ASC) WHERE status = 'pending';
