"""Release gates are explicit and fail closed; no status is inferred from file presence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GateStatus(str, Enum):  # noqa: UP042 - preserve existing str Enum behavior
    PASS = "pass"  # noqa: S105 - this is an enum status label, not a credential
    BLOCKED = "blocked"


@dataclass(frozen=True)
class GateItem:
    code: str
    description: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class PhaseGate:
    phase: str
    items: tuple[GateItem, ...]

    @property
    def status(self) -> GateStatus:
        return GateStatus.PASS if all(i.passed for i in self.items) else GateStatus.BLOCKED

    @property
    def blockers(self) -> tuple[GateItem, ...]:
        return tuple(i for i in self.items if not i.passed)


PHASE_1_GATE = PhaseGate(
    "1",
    (
        GateItem("P1-DB", "migrations from empty PostgreSQL", False, "requires staging run"),
        GateItem(
            "P1-REDIS",
            "Redis/arq integration and stuck-job recovery",
            False,
            "requires staging run",
        ),
        GateItem(
            "P1-CI", "ruff, mypy, import-linter, pytest", False, "requires dependency environment"
        ),
        GateItem(
            "P1-RACE", "one-time form and outbox concurrent tests", False, "requires PostgreSQL"
        ),
        GateItem("P1-RESTORE", "encrypted backup restore drill", False, "requires backup target"),
    ),
)

PHASE_2_GATE = PhaseGate(
    "2",
    (
        GateItem(
            "P2-TELEGRAM", "signed Telegram initData in deployed Mini App", False, "not deployed"
        ),
        GateItem(
            "P2-APPROVAL",
            "AuthContext + independent approval + audit",
            False,
            "integration test required",
        ),
        GateItem(
            "P2-WEBAUTHN",
            "real FIDO2/WebAuthn ceremony",
            False,
            "reviewed library/staging required",
        ),
        GateItem(
            "P2-SESSION",
            "session issuance only after approval and MFA",
            False,
            "integration test required",
        ),
    ),
)
