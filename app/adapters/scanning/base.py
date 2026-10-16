from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Finding:
    rule_code: str
    severity: str
    evidence: str
    confidence: float


class ContentScanner(Protocol):
    code: str

    async def scan_text(self, text: str) -> list[Finding]: ...
    async def scan_image(self, content: bytes, *, mime_type: str) -> list[Finding]: ...
