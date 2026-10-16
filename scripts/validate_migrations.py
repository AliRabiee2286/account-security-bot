"""Static migration sanity checks when PostgreSQL is unavailable."""

import re
from pathlib import Path

files = sorted(Path("migrations/versions").glob("*.py"))
if not files:
    raise SystemExit("no migrations")
revisions, parents = set(), set()
for path in files:
    text = path.read_text()
    revs = re.findall(r"\brevision\s*=\s*['\"]([^'\"]+)", text)
    downs = re.findall(r"\bdown_revision\s*=\s*(?:['\"]([^'\"]*)['\"]|None)", text)
    if len(revs) != 1 or len(downs) != 1:
        raise SystemExit(f"bad revision declaration: {path}")
    rev, parent = revs[0], downs[0]
    if rev in revisions:
        raise SystemExit(f"duplicate revision: {path}")
    revisions.add(rev)
    if parent:
        parents.add(parent)
heads = revisions - parents
if len(heads) != 1:
    raise SystemExit(f"expected one migration head, found {heads}")
print(f"migration chain static check: {len(files)} files, head={next(iter(heads))}")
