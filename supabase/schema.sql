CREATE TYPE user_role AS ENUM ('viewer', 'admin');
CREATE TYPE request_status AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE refresh_frequency AS ENUM ('daily', 'weekly', 'monthly', 'quarterly', 'ad_hoc');

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL UNIQUE,
    full_name     TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          user_role NOT NULL DEFAULT 'viewer',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE source_systems (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    hostname    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE classifications (
    id          SERIAL PRIMARY KEY,
    label       TEXT NOT NULL UNIQUE,
    rank        INT  NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE datasets (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              TEXT NOT NULL UNIQUE,
    description       TEXT,
    source_system_id  INT  NOT NULL REFERENCES source_systems(id),
    classification_id INT  NOT NULL REFERENCES classifications(id),
    owner_id          UUID NOT NULL REFERENCES users(id),
    row_count         BIGINT CHECK (row_count >= 0),
    refresh_frequency refresh_frequency NOT NULL DEFAULT 'daily',
    last_refreshed    DATE,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE access_requests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id   UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    requested_by UUID NOT NULL REFERENCES users(id),
    reason       TEXT NOT NULL,
    status       request_status NOT NULL DEFAULT 'pending',
    decided_by   UUID REFERENCES users(id),
    decided_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_decided CHECK (
        (status = 'pending'  AND decided_by IS NULL     AND decided_at IS NULL)
     OR (status <> 'pending' AND decided_by IS NOT NULL AND decided_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX uq_pending_request
    ON access_requests(dataset_id, requested_by)
    WHERE status = 'pending';
