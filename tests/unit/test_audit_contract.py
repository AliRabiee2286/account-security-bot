import subprocess
import sys
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_contract import SecurityAuditRecorder
from app.core.session_service import revoke_session
from app.modules.audit import api as audit
from app.modules.audit.service import record


def test_core_session_import_does_not_load_domain_modules():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import app.core.session_service; "
            "loaded = [name for name in sys.modules if name.startswith('app.modules')]; "
            "print(loaded); raise SystemExit(bool(loaded))",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


async def test_revoke_session_passes_event_to_injected_recorder():
    session = AsyncMock(spec=AsyncSession)
    actor_id, session_id = uuid4(), uuid4()
    events = []

    async def recorder(
        transaction: AsyncSession, *, action: str, actor_id: UUID, target_id: UUID
    ) -> None:
        session.execute.assert_awaited_once()
        events.append((transaction, action, actor_id, target_id))

    audit_recorder: SecurityAuditRecorder = recorder
    await revoke_session(
        session, session_id=session_id, actor_id=actor_id, audit_recorder=audit_recorder
    )

    assert events == [(session, "auth.session.revoked", actor_id, session_id)]
    statement, parameters = session.execute.await_args.args
    assert "revoked_at=now()" in str(statement)
    assert "revoked_at IS NULL" in str(statement)
    assert parameters == {"id": session_id}
    session.commit.assert_not_awaited()


async def test_revoke_session_propagates_audit_failure_to_transaction_owner():
    session = AsyncMock(spec=AsyncSession)
    recorder = AsyncMock(side_effect=RuntimeError("audit unavailable"))

    with pytest.raises(RuntimeError, match="audit unavailable"):
        await revoke_session(session, session_id=uuid4(), actor_id=uuid4(), audit_recorder=recorder)

    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_revoke_session_does_not_audit_a_failed_update():
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = RuntimeError("update failed")
    recorder = AsyncMock()

    with pytest.raises(RuntimeError, match="update failed"):
        await revoke_session(session, session_id=uuid4(), actor_id=uuid4(), audit_recorder=recorder)

    recorder.assert_not_awaited()


async def test_public_security_audit_adapter_preserves_record_payload(monkeypatch):
    assert audit.record is record
    assert {"Result", "record", "audit_security_event"} <= set(audit.__all__)
    record_mock = AsyncMock()
    monkeypatch.setattr(audit, "record", record_mock)
    session = AsyncMock(spec=AsyncSession)
    actor_id, target_id = uuid4(), uuid4()
    recorder: SecurityAuditRecorder = audit.audit_security_event

    await recorder(session, action="auth.session.revoked", actor_id=actor_id, target_id=target_id)

    record_mock.assert_awaited_once_with(
        session,
        action="auth.session.revoked",
        actor_type="employee",
        actor_id=str(actor_id),
        target_type="session",
        target_id=str(target_id),
    )
    session.commit.assert_not_awaited()
