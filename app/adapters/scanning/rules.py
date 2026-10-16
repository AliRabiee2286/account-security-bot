"""Conservative first-stage scanner. It flags for human review; it never deletes automatically."""

from __future__ import annotations

import re

from app.adapters.scanning.base import Finding

_RULES = {
    "internal-secret-marker": re.compile(r"(?i)\b(confidential|internal[- ]only|محرمانه|داخلی)\b"),
    "credential-like": re.compile(r"(?i)\b(password|passwd|api[_ -]?key|token|رمز|کلید)\b"),
}


async def scan_text(text: str) -> list[Finding]:
    return [
        Finding(
            code, "medium" if code == "internal-secret-marker" else "critical", m.group(0), 0.70
        )
        for code, pattern in _RULES.items()
        if (m := pattern.search(text))
    ]
