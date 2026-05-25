-- Full DSQL-compatible schema for Know-It-All Tutor System.
-- Replaces schema_v2.sql and incremental migrations 003-006.
--
-- DSQL restrictions applied:
--   - No foreign key constraints
--   - No triggers or PL/pgSQL functions
--   - No GIN/GIST indexes (B-tree only)
--   - No SERIAL/sequences — UUID PKs via gen_random_uuid()
--   - No uuid-ossp extension
--   - updated_at must be managed by application code

CREATE TABLE IF NOT EXISTS users (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_sub  VARCHAR(255) UNIQUE NOT NULL,
    email        VARCHAR(255) UNIQUE NOT NULL,
    first_name   VARCHAR(100),
    last_name    VARCHAR(100),
    is_active    BOOLEAN      DEFAULT true,
    created_at   TIMESTAMPTZ  DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  DEFAULT NOW(),
    last_login   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS tree_nodes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id   UUID,
    user_id     UUID        NOT NULL,
    node_type   VARCHAR(50) NOT NULL CHECK (node_type IN ('domain', 'category', 'term')),
    data        JSONB       NOT NULL,
    metadata    JSONB       DEFAULT '{}',
    is_public   BOOLEAN     NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL,
    domain_id           UUID        NOT NULL,
    status              VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
    current_term_index  INTEGER     DEFAULT 0,
    total_questions     INTEGER     DEFAULT 0,
    correct_answers     INTEGER     DEFAULT 0,
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    paused_at           TIMESTAMPTZ,
    session_data        JSONB       DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS progress_records (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID         NOT NULL,
    term_id          UUID         NOT NULL,
    session_id       UUID,
    student_answer   TEXT         NOT NULL,
    correct_answer   TEXT         NOT NULL,
    is_correct       BOOLEAN      NOT NULL,
    similarity_score DECIMAL(3,2) CHECK (similarity_score BETWEEN 0.0 AND 1.0),
    attempt_number   INTEGER      DEFAULT 1,
    feedback         TEXT,
    created_at       TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS batch_uploads (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id      UUID        NOT NULL,
    filename      VARCHAR(255) NOT NULL,
    subject_count INTEGER     NOT NULL,
    status        VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    uploaded_at   TIMESTAMPTZ DEFAULT NOW(),
    processed_at  TIMESTAMPTZ,
    error_message TEXT,
    metadata      JSONB       DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS domain_gen_jobs (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       TEXT        NOT NULL,
    topic         TEXT        NOT NULL,
    hints         TEXT        NOT NULL DEFAULT '',
    total_terms   INTEGER     NOT NULL DEFAULT 50,
    status        TEXT        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'complete', 'failed', 'approved')),
    output_json   JSONB,
    output_path   TEXT,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- tree_nodes indexes
CREATE INDEX ASYNC idx_tree_nodes_parent        ON tree_nodes (parent_id);
CREATE INDEX ASYNC idx_tree_nodes_user          ON tree_nodes (user_id);
CREATE INDEX ASYNC idx_tree_nodes_type          ON tree_nodes (node_type);
CREATE INDEX ASYNC idx_tree_nodes_user_type     ON tree_nodes (user_id, node_type);
CREATE INDEX ASYNC idx_tree_nodes_public        ON tree_nodes (is_public);
CREATE INDEX ASYNC idx_tree_nodes_domain_access ON tree_nodes (node_type, user_id, is_public);

-- progress_records indexes
CREATE INDEX ASYNC idx_progress_user_term    ON progress_records (user_id, term_id);
CREATE INDEX ASYNC idx_progress_session      ON progress_records (session_id);
CREATE INDEX ASYNC idx_progress_user_created ON progress_records (user_id, created_at);

-- quiz_sessions indexes
CREATE INDEX ASYNC idx_quiz_sessions_user        ON quiz_sessions (user_id);
CREATE INDEX ASYNC idx_quiz_sessions_domain      ON quiz_sessions (domain_id);
CREATE INDEX ASYNC idx_quiz_sessions_status      ON quiz_sessions (status);
CREATE INDEX ASYNC idx_quiz_sessions_user_status ON quiz_sessions (user_id, status);

-- batch_uploads indexes
CREATE INDEX ASYNC idx_batch_uploads_admin  ON batch_uploads (admin_id);
CREATE INDEX ASYNC idx_batch_uploads_status ON batch_uploads (status);

-- users indexes
CREATE INDEX ASYNC idx_users_email       ON users (email);
CREATE INDEX ASYNC idx_users_cognito_sub ON users (cognito_sub);
CREATE INDEX ASYNC idx_users_active      ON users (is_active);

-- domain_gen_jobs indexes
CREATE INDEX ASYNC idx_domain_gen_jobs_status ON domain_gen_jobs (status, created_at);
CREATE INDEX ASYNC idx_domain_gen_jobs_user   ON domain_gen_jobs (user_id, created_at DESC);
