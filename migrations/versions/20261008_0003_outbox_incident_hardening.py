"""Outbox delivery metadata and idempotent incident actions.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.execute("ALTER TABLE core.outbox ADD COLUMN IF NOT EXISTS last_error varchar(500)")
    op.execute("ALTER TABLE core.outbox ADD COLUMN IF NOT EXISTS delivered_at timestamptz")
    op.execute("ALTER TABLE core.outbox ADD COLUMN IF NOT EXISTS delivering_at timestamptz")
    op.execute("ALTER TABLE core.outbox DROP CONSTRAINT IF EXISTS outbox_status_check")
    op.execute(
        "ALTER TABLE core.outbox ADD CONSTRAINT outbox_status_check "
        "CHECK (status IN ('pending','delivering','delivered','failed','dead'))"
    )
    op.execute(
        "ALTER TABLE incidents.incidents ADD COLUMN IF NOT EXISTS idempotency_key varchar(128)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_incident_idempotency "
        "ON incidents.incidents(idempotency_key) "
        "WHERE idempotency_key IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_incident_idempotency")
    op.execute("ALTER TABLE incidents.incidents DROP COLUMN IF EXISTS idempotency_key")
    op.execute(
        "ALTER TABLE core.outbox DROP COLUMN IF EXISTS last_error, "
        "DROP COLUMN IF EXISTS delivered_at, DROP COLUMN IF EXISTS delivering_at"
    )
