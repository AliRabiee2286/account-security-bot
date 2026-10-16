from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, ValidationFailed
from app.core.idempotency import key as idempotency_key
from app.modules.audit import api as audit
from app.modules.incidents.models import Incident
from app.modules.incidents.schemas import IncidentDTO, IncidentReport


async def report(
    session: AsyncSession, *, request: IncidentReport, reporter_id: UUID, source: str = "employee"
) -> IncidentDTO:
    idem = idempotency_key(
        "incident.report", str(reporter_id), str(request.social_account_id), request.summary
    )
    existing = (
        await session.execute(select(Incident).where(Incident.idempotency_key == idem))
    ).scalar_one_or_none()
    if existing:
        return IncidentDTO.model_validate(existing)
    incident = Incident(
        severity=request.severity,
        source=source,
        owner_id=reporter_id,
        social_account_id=request.social_account_id,
        summary=request.summary,
        removal_deadline=datetime.now(UTC) + timedelta(hours=4),
        idempotency_key=idem,
    )
    session.add(incident)
    await session.flush()
    await audit.record(
        session,
        action="incident.reported",
        actor_type="employee",
        actor_id=str(reporter_id),
        target_type="incident",
        target_id=str(incident.id),
        metadata={"severity": request.severity, "source": source},
    )
    return IncidentDTO.model_validate(incident)


async def acknowledge(session: AsyncSession, *, incident_id: UUID, actor_id: UUID) -> IncidentDTO:
    incident = (
        await session.execute(select(Incident).where(Incident.id == incident_id).with_for_update())
    ).scalar_one_or_none()
    if incident is None:
        raise NotFound("incident")
    if incident.status not in ("open", "acknowledged"):
        raise ValidationFailed("incident is not actionable")
    incident.status = "acknowledged"
    await audit.record(
        session,
        action="incident.acknowledged",
        actor_type="employee",
        actor_id=str(actor_id),
        target_type="incident",
        target_id=str(incident.id),
    )
    return IncidentDTO.model_validate(incident)


async def mark_removal_pending(
    session: AsyncSession, *, incident_id: UUID, actor_id: UUID
) -> IncidentDTO:
    incident = (
        await session.execute(select(Incident).where(Incident.id == incident_id).with_for_update())
    ).scalar_one_or_none()
    if incident is None:
        raise NotFound("incident")
    incident.status = "removal_pending"
    await audit.record(
        session,
        action="incident.removal_pending",
        actor_type="employee",
        actor_id=str(actor_id),
        target_type="incident",
        target_id=str(incident.id),
    )
    return IncidentDTO.model_validate(incident)
