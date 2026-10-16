"""Catch SQLAlchemy `Mapped[object]` annotations that cannot infer a SQL type."""

from pathlib import Path

bad = []
for path in Path("app").rglob("models.py"):
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if "Mapped[object" in line:
            bad.append(f"{path}:{number}:{line.strip()}")
if bad:
    raise SystemExit("\n".join(bad))
print("model annotation scan: ok")
