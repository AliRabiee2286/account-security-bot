"""Two-person approval records.

Revision ID: 0006
Revises: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade():
    op.execute("""
    CREATE TABLE identity.approval_requests (
      id uuid PRIMARY KEY, action varchar(100) NOT NULL, target_type varchar(50) NOT NULL,
      target_id uuid NOT NULL, requested_by uuid NOT NULL REFERENCES identity.employees(id),
      approved_by uuid REFERENCES identity.employees(id), approved_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(),
      CONSTRAINT ck_approval_not_self CHECK (approved_by IS NULL OR approved_by <> requested_by)
    );
    GRANT SELECT, INSERT, UPDATE ON identity.approval_requests TO sentinel_app_role;
    REVOKE DELETE ON identity.approval_requests FROM sentinel_app_role;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS identity.approval_requests")
