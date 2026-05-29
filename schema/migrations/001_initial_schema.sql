-- Migration 001: Core schema

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    identity    JSONB       NOT NULL,
    profile     JSONB       NOT NULL DEFAULT '{}',
    documents   JSONB       NOT NULL DEFAULT '{}',
    location    JSONB       NOT NULL DEFAULT '{}',
    meta        JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_identity_email    ON users ((identity->>'email'));
CREATE INDEX idx_users_identity_phone    ON users ((identity->>'phone'));
CREATE INDEX idx_users_updated_at        ON users (updated_at);
CREATE INDEX idx_users_profile_gin       ON users USING gin (profile);
CREATE INDEX idx_users_location_gin      ON users USING gin (location);

-- Append-only change history; never updated or deleted
CREATE TABLE user_history (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id),
    field_path  TEXT        NOT NULL,
    old_value   JSONB,
    new_value   JSONB,
    changed_by  UUID        NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_history_user_id    ON user_history (user_id, changed_at DESC);
CREATE INDEX idx_user_history_field_path ON user_history (user_id, field_path);

-- Consent grants: one row per (user, grantee, scope set)
CREATE TABLE consent_grants (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id),
    grantee_id  UUID        NOT NULL,
    scope       TEXT[]      NOT NULL,
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ
);

CREATE INDEX idx_consent_grantee        ON consent_grants (grantee_id, user_id);
CREATE INDEX idx_consent_user           ON consent_grants (user_id);

-- Auto-update updated_at on users
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
