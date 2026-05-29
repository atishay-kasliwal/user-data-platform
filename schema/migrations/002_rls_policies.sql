-- Migration 002: Row-Level Security
-- Services connect as role 'service_role'; each request sets app.current_grantee_id.
-- Note: RLS only applies to non-superuser roles. The demo services connect as
-- the platform superuser for simplicity; in production they'd connect as
-- service_role with a session-scoped SET LOCAL app.current_grantee_id.

-- Create the roles the policies depend on (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'user_role') THEN
        CREATE ROLE user_role NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'platform_role') THEN
        CREATE ROLE platform_role NOLOGIN;
    END IF;
END$$;

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- A service can read a user row only if an active, non-expired consent grant exists
CREATE POLICY service_read_policy ON users
    FOR SELECT
    TO service_role
    USING (
        EXISTS (
            SELECT 1 FROM consent_grants cg
            WHERE cg.user_id       = users.id
              AND cg.grantee_id    = current_setting('app.current_grantee_id')::UUID
              AND cg.revoked_at    IS NULL
              AND (cg.expires_at IS NULL OR cg.expires_at > now())
        )
    );

-- Users (via user_role) can always read their own row
CREATE POLICY user_read_own_policy ON users
    FOR SELECT
    TO user_role
    USING (id = current_setting('app.current_user_id')::UUID);

-- Only the platform internal role can insert/update
CREATE POLICY platform_write_policy ON users
    FOR ALL
    TO platform_role
    USING (true)
    WITH CHECK (true);
