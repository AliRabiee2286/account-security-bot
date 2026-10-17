"""Foundation: schemas, identity, append-only partitioned audit, outbox, seed roles.

Revision ID: 0001
Revises:
"""

from alembic import op

from app.modules.identity.permissions import CATALOGUE, DEFAULT_ROLES

revision = "0001"
down_revision = None

ROLE_NAMES = {
    "super_observer": "ناظر کل",
    "security_lead": "مدیر ارشد امنیت",
    "department_manager": "مدیر بخش",
    "support": "پشتیبان",
    "employee": "کارمند",
}


def upgrade() -> None:
    for schema in ("core", "identity", "audit"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    op.execute("""
    CREATE TABLE identity.departments (
        id uuid PRIMARY KEY,
        name varchar(200) NOT NULL,
        parent_id uuid REFERENCES identity.departments(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    );
    """)
    op.execute("""
    CREATE TABLE identity.roles (
        id uuid PRIMARY KEY,
        code varchar(50) NOT NULL UNIQUE,
        name varchar(100) NOT NULL,
        parent_role_id uuid REFERENCES identity.roles(id),
        is_observer boolean NOT NULL DEFAULT false,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_roles_not_self_parent CHECK (parent_role_id IS DISTINCT FROM id)
    );
    """)
    op.execute("""
    CREATE TABLE identity.permissions (
        code varchar(80) PRIMARY KEY,
        requires_second_approval boolean NOT NULL DEFAULT false,
        observer_may_execute boolean NOT NULL DEFAULT true
    );
    """)
    op.execute("""
    CREATE TABLE identity.role_permissions (
        role_id uuid NOT NULL REFERENCES identity.roles(id),
        permission_code varchar(80) NOT NULL REFERENCES identity.permissions(code),
        PRIMARY KEY (role_id, permission_code)
    );
    """)
    op.execute("""
    CREATE TABLE identity.employees (
        id uuid PRIMARY KEY,
        telegram_user_id bigint NOT NULL UNIQUE,
        full_name varchar(200) NOT NULL,
        status varchar(20) NOT NULL DEFAULT 'pending'
            CONSTRAINT ck_employees_status_valid
            CHECK (status IN ('pending','active','suspended','offboarded')),
        role_id uuid NOT NULL REFERENCES identity.roles(id),
        department_id uuid REFERENCES identity.departments(id),
        approved_by uuid REFERENCES identity.employees(id),
        approved_at timestamptz,
        offboarded_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    );
    """)
    op.execute("CREATE INDEX ix_employees_department ON identity.employees(department_id)")
    op.execute("CREATE INDEX ix_employees_status ON identity.employees(status)")

    # Append-only audit log, partitioned monthly (database principle #7).
    op.execute("""
    CREATE TABLE audit.audit_events (
        id uuid NOT NULL,
        occurred_at timestamptz NOT NULL DEFAULT now(),
        request_id varchar(64) NOT NULL,
        actor_type varchar(30) NOT NULL,
        actor_id varchar(64),
        action varchar(100) NOT NULL,
        target_type varchar(50),
        target_id varchar(64),
        result varchar(20) NOT NULL CHECK (result IN ('success','denied','error')),
        reason varchar(500),
        metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
        prev_hash varchar(64),
        row_hash varchar(64) NOT NULL,
        PRIMARY KEY (id, occurred_at)
    ) PARTITION BY RANGE (occurred_at);
    """)
    op.execute("CREATE INDEX ix_audit_actor_time ON audit.audit_events(actor_id, occurred_at)")
    op.execute("CREATE INDEX ix_audit_target ON audit.audit_events(target_type, target_id)")
    op.execute("CREATE INDEX ix_audit_request ON audit.audit_events(request_id)")
    op.execute("""
    CREATE OR REPLACE FUNCTION audit.ensure_partition(month_start date) RETURNS void AS $$
    DECLARE
        part text := 'audit_events_' || to_char(month_start, 'YYYY_MM');
    BEGIN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS audit.%I PARTITION OF audit.audit_events
             FOR VALUES FROM (%L) TO (%L)',
            part, month_start, (month_start + interval '1 month')::date);
    END $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    SELECT audit.ensure_partition(
        (date_trunc('month', now())::date + (i || ' month')::interval)::date
    )
    FROM generate_series(0, 3) AS i;
    """)
    op.execute("CREATE TABLE audit.audit_events_default PARTITION OF audit.audit_events DEFAULT")
    op.execute("""
    CREATE OR REPLACE FUNCTION audit.forbid_mutation() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit.audit_events is append-only';
    END $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trg_audit_no_update BEFORE UPDATE OR DELETE ON audit.audit_events
        FOR EACH ROW EXECUTE FUNCTION audit.forbid_mutation();
    """)
    op.execute("""
    CREATE TRIGGER trg_audit_no_truncate BEFORE TRUNCATE ON audit.audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION audit.forbid_mutation();
    """)

    op.execute("""
    CREATE TABLE core.outbox (
        id uuid PRIMARY KEY,
        event_type varchar(100) NOT NULL,
        payload jsonb NOT NULL,
        request_id varchar(64) NOT NULL,
        status varchar(20) NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending','delivered','failed','dead')),
        attempts integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        available_at timestamptz NOT NULL DEFAULT now()
    );
    """)
    op.execute(
        "CREATE INDEX ix_outbox_pending ON core.outbox(available_at) WHERE status = 'pending'"
    )

    # Seed permission catalogue and the D-007 role skeleton (gen_random_uuid ok for seeds).
    for p in CATALOGUE.values():
        op.execute(
            "INSERT INTO identity.permissions VALUES "  # noqa: S608 - migration seeds use controlled constants
            f"('{p.code}', {str(p.requires_second_approval).lower()}, "
            f"{str(p.observer_may_execute).lower()})"
        )
    for code, (parent, perms) in DEFAULT_ROLES.items():
        parent_sql = (
            f"(SELECT id FROM identity.roles WHERE code = '{parent}')"  # noqa: S608 - controlled role seed
            if parent
            else "NULL"
        )
        observer = "true" if code == "super_observer" else "false"
        op.execute(
            "INSERT INTO identity.roles (id, code, name, parent_role_id, is_observer) VALUES "  # noqa: S608 - controlled role seed
            f"(gen_random_uuid(), '{code}', '{ROLE_NAMES[code]}', {parent_sql}, {observer})"
        )
        for perm in perms:
            op.execute(
                "INSERT INTO identity.role_permissions "  # noqa: S608 - controlled permission seed
                f"SELECT id, '{perm}' FROM identity.roles WHERE code = '{code}'"
            )

    # Least-privilege DB role for the app: may INSERT/SELECT audit, never UPDATE/DELETE (S-018).
    op.execute("""
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sentinel_app_role') THEN
            CREATE ROLE sentinel_app_role NOLOGIN;
        END IF;
    END $$;
    """)
    op.execute("GRANT sentinel_app_role TO sentinel_app")
    op.execute("GRANT USAGE ON SCHEMA core, identity, audit TO sentinel_app_role")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA identity, core TO sentinel_app_role"
    )
    op.execute("GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA audit TO sentinel_app_role")


def downgrade() -> None:
    # Audit data is never dropped by a migration downgrade. Drop app tables only in dev.
    op.execute("DROP TABLE IF EXISTS core.outbox")
    op.execute(
        "DROP TABLE IF EXISTS identity.employees, identity.role_permissions, "
        "identity.permissions, identity.roles, identity.departments"
    )
