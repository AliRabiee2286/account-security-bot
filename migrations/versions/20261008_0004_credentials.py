"""Encrypted credential vault rows and form subjects.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.execute("""
    CREATE TABLE social.credentials (
        id uuid PRIMARY KEY,
        owner_type varchar(30) NOT NULL CHECK (owner_type IN ('social_account','mailbox')),
        owner_id uuid NOT NULL,
        ciphertext bytea NOT NULL,
        wrapped_dek bytea NOT NULL,
        key_version integer NOT NULL,
        auth_type varchar(30) NOT NULL,
        rotated_at timestamptz,
        last_accessed_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_credentials_owner ON social.credentials(owner_type, owner_id);
    REVOKE DELETE ON social.credentials FROM sentinel_app_role;
    GRANT SELECT, INSERT, UPDATE ON social.credentials TO sentinel_app_role;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS social.credentials")
