-- Migration 002: Row-Level Security
-- Services connect as role 'service_role'; each request sets app.current_grantee_id

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
