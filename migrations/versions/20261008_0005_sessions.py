"""Session hashes and MFA enrollment metadata.

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    op.execute("""
    CREATE TABLE identity.sessions (
      id uuid PRIMARY KEY,
      employee_id uuid NOT NULL REFERENCES identity.employees(id),
      token_hash varchar(64) NOT NULL UNIQUE,
      expires_at timestamptz NOT NULL,
      revoked_at timestamptz,
      amr varchar(200) NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(),
      last_seen_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_sessions_active ON identity.sessions(employee_id, expires_at)
      WHERE revoked_at IS NULL;
    CREATE TABLE identity.mfa_credentials (
      id uuid PRIMARY KEY,
      employee_id uuid NOT NULL REFERENCES identity.employees(id),
      credential_id bytea NOT NULL UNIQUE,
      public_key bytea NOT NULL,
      sign_count bigint NOT NULL DEFAULT 0,
      revoked_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now()
    );
    GRANT SELECT, INSERT, UPDATE ON identity.sessions,
      identity.mfa_credentials TO sentinel_app_role;
    REVOKE DELETE ON identity.sessions, identity.mfa_credentials FROM sentinel_app_role;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS identity.mfa_credentials, identity.sessions")
