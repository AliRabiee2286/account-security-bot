"""Unit tests for RBAC (D-009: pure, no DB)."""

from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Employee, Permission, Role
from app.modules.identity.permissions import CATALOGUE, DEFAULT_ROLES
from app.modules.identity.rbac import (
    PermissionDef,
    RoleGraph,
    RoleNode,
    authorize,
    department_subtree,
)
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.service import authorize_employee_action


@pytest.fixture
def role_graph() -> RoleGraph:
    roles_dict = DEFAULT_ROLES
    id_map: dict[str, UUID] = {}
    for code in roles_dict:
        id_map[code] = uuid4()
    nodes = []
    for code, (parent, perms) in roles_dict.items():
        nodes.append(
            RoleNode(
                id=id_map[code],
                code=code,
                parent_id=id_map[parent] if parent else None,
                permissions=frozenset(perms),
            )
        )
    return RoleGraph(nodes)


def test_permission_inheritance(role_graph: RoleGraph) -> None:
    super_observer_id = next(r.id for r in role_graph._roles.values() if r.code == "super_observer")
    perms = role_graph.effective_permissions(super_observer_id)
    assert "audit.view" in perms
    support_id = next(r.id for r in role_graph._roles.values() if r.code == "support")
    assert "employee.approve" in role_graph.effective_permissions(support_id)
    assert "employee.self.view" in role_graph.effective_permissions(support_id)
    assert "audit.view" not in role_graph.effective_permissions(support_id)
    assert "incident.content.remove" not in role_graph.effective_permissions(support_id)
    manager_id = next(r.id for r in role_graph._roles.values() if r.code == "department_manager")
    assert "employee.approve" in role_graph.effective_permissions(manager_id)
    assert "incident.content.remove" in role_graph.effective_permissions(manager_id)
    employee_id = next(r.id for r in role_graph._roles.values() if r.code == "employee")
    assert role_graph.effective_permissions(employee_id) == frozenset({"employee.self.view"})


def test_support_can_only_use_explicit_or_descendant_permissions(role_graph: RoleGraph) -> None:
    support_id = next(r.id for r in role_graph._roles.values() if r.code == "support")
    for permission, allowed in [
        ("employee.approve", True),
        ("audit.view", False),
        ("incident.content.remove", False),
    ]:
        decision = authorize(
            graph=role_graph,
            perms=CATALOGUE,
            actor_role=support_id,
            actor_is_observer=False,
            permission=permission,
            actor_scope=None,
            target_department=None,
        )
        assert decision.allowed is allowed
        if not allowed:
            assert decision.reason == "missing_permission"

    nodes = [
        RoleNode(
            r.id,
            r.code,
            r.parent_id,
            r.permissions | {"audit.view", "incident.content.remove"},
        )
        if r.id == support_id
        else r
        for r in role_graph._roles.values()
    ]
    assigned_graph = RoleGraph(nodes)
    audit_decision = authorize(
        graph=assigned_graph,
        perms=CATALOGUE,
        actor_role=support_id,
        actor_is_observer=False,
        permission="audit.view",
        actor_scope=None,
        target_department=None,
    )
    assert audit_decision.allowed
    removal_decision = authorize(
        graph=assigned_graph,
        perms=CATALOGUE,
        actor_role=support_id,
        actor_is_observer=False,
        permission="incident.content.remove",
        actor_scope=None,
        target_department=None,
    )
    assert removal_decision.allowed
    assert removal_decision.needs_second_approval


@pytest.mark.parametrize("permission", ["employee.self.view", "employee.view", "audit.view"])
@pytest.mark.parametrize("operation", ["view", "execute"])
def test_observer_visibility_does_not_grant_execution(
    permission: str, operation: Literal["view", "execute"]
) -> None:
    observer_id = uuid4()
    graph = RoleGraph([RoleNode(observer_id, "super_observer", None, frozenset())])
    decision = authorize(
        graph=graph,
        perms=CATALOGUE,
        actor_role=observer_id,
        actor_is_observer=True,
        permission=permission,
        actor_scope=None,
        target_department=None,
        operation=operation,
    )
    assert decision.allowed is (operation == "view")
    assert not decision.needs_second_approval
    if operation == "execute":
        assert decision.reason == "missing_permission"


def test_observer_visibility_catalogue_is_an_explicit_allowlist() -> None:
    assert {p.code for p in CATALOGUE.values() if p.observer_may_view} == {
        "employee.self.view",
        "employee.view",
        "audit.view",
    }
    assert not PermissionDef("custom.view").observer_may_view


@pytest.mark.parametrize("actor_is_observer", [True, False])
@pytest.mark.parametrize(
    "permission",
    [
        "employee.approve",
        "employee.suspend",
        "employee.offboard",
        "role.assign",
        "mailbox.seed.view",
        "incident.content.remove",
    ],
)
def test_view_cannot_authorize_non_read_permissions(
    role_graph: RoleGraph, actor_is_observer: bool, permission: str
) -> None:
    role_id = next(r.id for r in role_graph._roles.values() if r.code == "super_observer")
    decision = authorize(
        graph=role_graph,
        perms=CATALOGUE,
        actor_role=role_id,
        actor_is_observer=actor_is_observer,
        permission=permission,
        actor_scope=None,
        target_department=None,
        operation="view",
    )
    assert not decision.allowed
    assert decision.reason == "not_view_permission"


@pytest.mark.parametrize("target_in_scope", [True, False])
def test_observer_visibility_preserves_scope(target_in_scope: bool) -> None:
    observer_id, department_id = uuid4(), uuid4()
    graph = RoleGraph([RoleNode(observer_id, "super_observer", None, frozenset())])
    decision = authorize(
        graph=graph,
        perms=CATALOGUE,
        actor_role=observer_id,
        actor_is_observer=True,
        permission="employee.view",
        actor_scope=frozenset({department_id}),
        target_department=department_id if target_in_scope else None,
        operation="view",
    )
    assert decision.allowed is target_in_scope
    if not target_in_scope:
        assert decision.reason == "out_of_scope"


def test_non_observer_view_requires_membership() -> None:
    role_id = uuid4()
    graph = RoleGraph([RoleNode(role_id, "employee", None, frozenset())])
    decision = authorize(
        graph=graph,
        perms=CATALOGUE,
        actor_role=role_id,
        actor_is_observer=False,
        permission="employee.view",
        actor_scope=None,
        target_department=None,
        operation="view",
    )
    assert not decision.allowed
    assert decision.reason == "missing_permission"


@pytest.mark.parametrize("operation", ["view", "execute"])
def test_unknown_permission_fails_closed(
    role_graph: RoleGraph, operation: Literal["view", "execute"]
) -> None:
    role_id = next(r.id for r in role_graph._roles.values() if r.code == "super_observer")
    decision = authorize(
        graph=role_graph,
        perms=CATALOGUE,
        actor_role=role_id,
        actor_is_observer=True,
        permission="unknown.view",
        actor_scope=None,
        target_department=None,
        operation=operation,
    )
    assert not decision.allowed
    assert decision.reason == "unknown_permission"


@pytest.mark.parametrize("operation", ["view", "execute"])
def test_view_flag_never_bypasses_observer_execution_denial(
    operation: Literal["view", "execute"],
) -> None:
    role_id = uuid4()
    graph = RoleGraph([RoleNode(role_id, "super_observer", None, frozenset({"employee.view"}))])
    perms = {
        "employee.view": PermissionDef(
            "employee.view",
            observer_may_execute=False,
            observer_may_view=True,
        )
    }
    decision = authorize(
        graph=graph,
        perms=perms,
        actor_role=role_id,
        actor_is_observer=True,
        permission="employee.view",
        actor_scope=None,
        target_department=None,
        operation=operation,
    )
    assert decision.allowed is (operation == "view")
    if operation == "execute":
        assert decision.reason == "observer_cannot_execute"


async def test_repository_derives_visibility_without_database_column() -> None:
    rows = [
        Permission(
            code=p.code,
            requires_second_approval=p.requires_second_approval,
            observer_may_execute=p.observer_may_execute,
        )
        for p in CATALOGUE.values()
    ]
    rows.append(
        Permission(code="custom.view", requires_second_approval=False, observer_may_execute=False)
    )
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute.return_value = result
    definitions = await IdentityRepository(session).permission_defs()
    assert {p.code for p in definitions.values() if p.observer_may_view} == {
        "employee.self.view",
        "employee.view",
        "audit.view",
    }
    for row in rows:
        assert definitions[row.code].requires_second_approval == row.requires_second_approval
        assert definitions[row.code].observer_may_execute == row.observer_may_execute
    assert not definitions["custom.view"].observer_may_view


@pytest.mark.parametrize("operation", ["view", None])
async def test_public_check_forwards_view_and_defaults_to_execute(operation: str | None) -> None:
    role_id = uuid4()
    actor = Employee(id=uuid4(), role_id=role_id, status="active")
    target = Employee(id=uuid4(), department_id=uuid4())
    repo = MagicMock(spec=IdentityRepository)
    repo.get.side_effect = [actor, target]
    repo.role.return_value = Role(id=role_id, code="super_observer", is_observer=True)
    repo.role_graph.return_value = RoleGraph(
        [
            RoleNode(role_id, "super_observer", None, frozenset()),
        ]
    )
    repo.permission_defs.return_value = CATALOGUE
    with (
        patch("app.modules.identity.service.IdentityRepository", return_value=repo),
        patch("app.modules.identity.service.audit.record", new_callable=AsyncMock),
    ):
        session = AsyncMock(spec=AsyncSession)
        if operation == "view":
            decision = await authorize_employee_action(
                session,
                actor_id=actor.id,
                permission="employee.view",
                target_id=target.id,
                operation="view",
            )
        else:
            decision = await authorize_employee_action(
                session,
                actor_id=actor.id,
                permission="employee.view",
                target_id=target.id,
            )
    assert decision.allowed is (operation == "view")
    if operation is None:
        assert decision.reason == "missing_permission"


def test_observer_cannot_execute_destructive(role_graph: RoleGraph) -> None:
    observer_id = next(r.id for r in role_graph._roles.values() if r.code == "super_observer")
    decision = authorize(
        graph=role_graph,
        perms=CATALOGUE,
        actor_role=observer_id,
        actor_is_observer=True,
        permission="employee.offboard",
        actor_scope=None,
        target_department=None,
    )
    assert not decision.allowed
    assert decision.reason == "observer_cannot_execute"


def test_self_action_on_sensitive_fails(role_graph: RoleGraph) -> None:
    security_id = next(r.id for r in role_graph._roles.values() if r.code == "security_lead")
    emp_id = uuid4()
    decision = authorize(
        graph=role_graph,
        perms=CATALOGUE,
        actor_role=security_id,
        actor_is_observer=False,
        permission="role.assign",
        actor_scope=None,
        target_department=None,
        actor_id=emp_id,
        target_employee_id=emp_id,
    )
    assert not decision.allowed
    assert decision.reason == "self_action_on_sensitive"


def test_department_scope(role_graph: RoleGraph) -> None:
    managers = [uuid4(), uuid4(), uuid4()]
    parents = {managers[0]: None, managers[1]: managers[0], managers[2]: managers[0]}
    subtree = department_subtree(managers[0], parents)
    assert subtree == frozenset(managers)
    subtree = department_subtree(managers[2], parents)
    assert subtree == frozenset([managers[2]])
