"""Bind one-time form to exact target entity; prevent storing credentials on employee UUID.
Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade() -> None:
    # Revoke legacy tokens: they were not bound to an exact owner entity.
    op.execute("DELETE FROM social.one_time_forms")
    op.execute("ALTER TABLE social.one_time_forms ADD COLUMN owner_type varchar(30)")
    op.execute("ALTER TABLE social.one_time_forms ADD COLUMN owner_id uuid")
    op.execute(
        "ALTER TABLE social.one_time_forms ADD CONSTRAINT ck_form_owner_type "
        "CHECK (owner_type IN ('social_account','mailbox'))"
    )
    op.execute("ALTER TABLE social.one_time_forms ALTER COLUMN owner_type SET NOT NULL")
    op.execute("ALTER TABLE social.one_time_forms ALTER COLUMN owner_id SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE social.one_time_forms DROP COLUMN owner_type, DROP COLUMN owner_id")
