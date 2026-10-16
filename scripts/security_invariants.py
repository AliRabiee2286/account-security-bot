from pathlib import Path

checks = {
    "webhook secret guard": ("app/entrypoints/api/main.py", "is_valid_webhook"),
    "initData HMAC": ("app/core/telegram_init_data.py", "hmac.new"),
    "session hash lookup": ("app/core/auth_resolver.py", "hash_token(raw)"),
    "one-time atomic consume": ("app/core/one_time_form_store.py", "consumed_at IS NULL"),
    "audit redaction": ("app/modules/audit/service.py", "redact(metadata or {})"),
    "audit append-only trigger": (
        "migrations/versions/20261008_0001_foundation.py",
        "forbid_mutation",
    ),
    "dual approval constraint": (
        "migrations/versions/20261008_0006_approvals.py",
        "ck_approval_not_self",
    ),
    "egress HTTPS policy": ("app/adapters/http_policy.py", '"https"'),
    "no Telegram credential route": ("app/modules/social/service.py", "one-time secure form"),
    "Postgres outbox lock clause": (
        "app/core/outbox_dispatch.py",
        "LIMIT 1 FOR UPDATE SKIP LOCKED",
    ),
    "form origin validation": ("app/entrypoints/api/forms.py", 'request.headers.get("origin")'),
    "outbox lease timestamp": ("app/core/outbox_dispatch.py", "delivering_at = now()"),
}
for name, (file, needle) in checks.items():
    text = Path(file).read_text()
    if needle not in text:
        raise SystemExit(f"missing invariant: {name}")
    print(f"PASS {name}")
print(f"{len(checks)} offline security invariants passed")
