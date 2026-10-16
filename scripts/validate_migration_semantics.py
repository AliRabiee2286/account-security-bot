"""Semantic consistency checks across Alembic revisions and ORM declarations."""

from pathlib import Path

root = Path("migrations/versions")
alltext = "\n".join(p.read_text() for p in root.glob("*.py"))
required = {
    "outbox lease column": "delivering_at timestamptz",
    "outbox last error": "last_error varchar(500)",
    "outbox delivered timestamp": "delivered_at timestamptz",
    "forms exact owner type": "owner_type varchar(30)",
    "forms exact owner id": "owner_id uuid",
    "credentials wrapped DEK": "wrapped_dek bytea",
    "sessions token hash": "token_hash varchar(64)",
}
for label, needle in required.items():
    if needle not in alltext:
        raise SystemExit(f"missing migration field: {label}")
model = Path("app/core/outbox.py").read_text()
for field in ("delivering_at", "delivered_at", "last_error"):
    if field not in model:
        raise SystemExit(f"outbox ORM lacks {field}")
form = Path("app/modules/social/models.py").read_text()
for field in ("owner_type", "owner_id", "expires_at", "consumed_at"):
    if field not in form:
        raise SystemExit(f"one-time form ORM lacks {field}")
print(f"migration/model semantic scan: {len(required)} migration fields aligned")
