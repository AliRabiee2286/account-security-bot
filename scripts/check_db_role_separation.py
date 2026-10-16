"""Ensure migrations grant a NOLOGIN role and runtime never uses migration URL."""

import re
from pathlib import Path

base = Path("migrations/versions/20261008_0001_foundation.py").read_text()
if "CREATE ROLE sentinel_app_role NOLOGIN" not in base:
    raise SystemExit("missing NOLOGIN application role declaration")
if "GRANT sentinel_app_role TO sentinel_app" not in base:
    raise SystemExit("missing application role membership grant")
for path in Path("migrations/versions").glob("*.py"):
    text = path.read_text()
    if re.search(
        r"GRANT\s+(?:USAGE|SELECT|INSERT|UPDATE|DELETE|ALL).*?\bTO sentinel_app\s*[;.]",
        text,
        re.S,
    ):
        raise SystemExit(f"runtime role grant found in {path}")
config = Path("app/core/db.py").read_text()
if "get_settings().database_url" not in config:
    raise SystemExit("runtime database URL is not used by the application")
if "migration_database_url" in config:
    raise SystemExit("migration database URL must not be used by the application")
print("database role separation scan: ok")
