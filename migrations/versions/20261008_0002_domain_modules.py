"""Mailbox, social, one-time form, and incident domain tables.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS mailboxes")
    op.execute("CREATE SCHEMA IF NOT EXISTS social")
    op.execute("CREATE SCHEMA IF NOT EXISTS incidents")
    op.execute("""
    CREATE TABLE mailboxes.mailboxes (
        id uuid PRIMARY KEY,
        provider varchar(50) NOT NULL,
        provider_ref varchar(200) UNIQUE,
        address varchar(320) NOT NULL UNIQUE,
        status varchar(20) NOT NULL DEFAULT 'pending'
          CHECK (status IN ('pending','active','suspended','revoked')),
        current_owner_id uuid REFERENCES identity.employees(id),
        quota_group varchar(100),
        recovery_secret_ciphertext bytea,
        recovery_key_version integer,
        suspended_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_mailboxes_owner ON mailboxes.mailboxes(current_owner_id);
    CREATE INDEX ix_mailboxes_status ON mailboxes.mailboxes(status);

    CREATE TABLE mailboxes.assignments (
        id uuid PRIMARY KEY,
        mailbox_id uuid NOT NULL REFERENCES mailboxes.mailboxes(id),
        employee_id uuid NOT NULL REFERENCES identity.employees(id),
        assigned_at timestamptz NOT NULL DEFAULT now(),
        revoked_at timestamptz,
        assigned_by uuid NOT NULL REFERENCES identity.employees(id),
        reason varchar(500),
        CONSTRAINT ck_assignment_dates CHECK (revoked_at IS NULL OR revoked_at >= assigned_at)
    );
    CREATE INDEX ix_assignments_mailbox ON mailboxes.assignments(mailbox_id, assigned_at DESC);
    CREATE UNIQUE INDEX uq_active_mailbox_assignment ON mailboxes.assignments(mailbox_id)
      WHERE revoked_at IS NULL;
    """)
    op.execute("""
    CREATE TABLE social.social_accounts (
        id uuid PRIMARY KEY,
        platform varchar(30) NOT NULL CHECK (platform IN ('instagram','x','telegram')),
        handle varchar(255) NOT NULL,
        mailbox_id uuid NOT NULL REFERENCES mailboxes.mailboxes(id),
        owner_id uuid NOT NULL REFERENCES identity.employees(id),
        purpose varchar(500) NOT NULL,
        status varchar(30) NOT NULL DEFAULT 'submitted'
          CHECK (status IN (
            'submitted','support_approved','verifying','verified',
            'verification_failed','suspended'
          )),
        auth_type varchar(30) NOT NULL CHECK (auth_type IN ('oauth','manual')),
        oauth_token_ciphertext bytea,
        oauth_key_version integer,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(platform, handle)
    );
    CREATE INDEX ix_social_owner ON social.social_accounts(owner_id);
    CREATE INDEX ix_social_status ON social.social_accounts(status);

    CREATE TABLE social.one_time_forms (
        token_hash varchar(64) PRIMARY KEY,
        subject_id uuid NOT NULL,
        purpose varchar(50) NOT NULL,
        expires_at timestamptz NOT NULL,
        consumed_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_form_purpose CHECK (
          purpose IN ('social_oauth','credential_entry','seed_recovery')
        )
    );
    CREATE INDEX ix_forms_expiry ON social.one_time_forms(expires_at)
      WHERE consumed_at IS NULL;
    """)
    op.execute("""
    CREATE TABLE incidents.incidents (
        id uuid PRIMARY KEY,
        severity varchar(20) NOT NULL CHECK (severity IN ('low','medium','critical')),
        status varchar(30) NOT NULL DEFAULT 'open'
          CHECK (status IN (
            'open','acknowledged','removal_pending','secured','resolved','false_positive'
          )),
        source varchar(30) NOT NULL CHECK (source IN ('employee','admin','scanner')),
        owner_id uuid NOT NULL REFERENCES identity.employees(id),
        social_account_id uuid REFERENCES social.social_accounts(id),
        summary text NOT NULL,
        evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
        removal_deadline timestamptz,
        resolved_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_incidents_open_deadline ON incidents.incidents(removal_deadline)
      WHERE status IN ('open','acknowledged','removal_pending');
    """)
    # Grant only what the app needs. No blanket DELETE for sensitive domains.
    op.execute("""
    GRANT USAGE ON SCHEMA mailboxes, social, incidents TO sentinel_app_role;
    GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA
      mailboxes, social, incidents TO sentinel_app_role;
    REVOKE DELETE ON ALL TABLES IN SCHEMA mailboxes, social, incidents FROM sentinel_app_role;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS incidents.incidents")
    op.execute("DROP TABLE IF EXISTS social.one_time_forms, social.social_accounts")
    op.execute("DROP TABLE IF EXISTS mailboxes.assignments, mailboxes.mailboxes")
