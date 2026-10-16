"""S-006/S-007/D-007: hierarchical RBAC with inheritance + inherited scope. Pure and testable.

Role tree: parent_role_id points UP (Super Observer is the root).
A role inherits every permission of the roles BELOW it (its descendants).
Scope: a user with department D may act on employees in D and all sub-departments of D.
Sensitive permissions (requires_second_approval) are never executable by one person alone.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class RoleNode:
    id: UUID
    code: str
    parent_id: UUID | None
    permissions: frozenset[str]


@dataclass(frozen=True)
class PermissionDef:
    code: str
    requires_second_approval: bool = False
    observer_may_execute: bool = True  # S-007: False for destructive/sensitive actions
    observer_may_view: bool = False  # Explicit read-only visibility; never an execution grant


class RoleGraph:
    def __init__(self, roles: Iterable[RoleNode]) -> None:
        self._roles = {r.id: r for r in roles}
        self._children: dict[UUID, list[UUID]] = defaultdict(list)
        for r in self._roles.values():
            if r.parent_id is not None:
                if r.parent_id not in self._roles:
                    raise ValueError(f"role {r.code}: unknown parent")
                self._children[r.parent_id].append(r.id)
        self._check_acyclic()
        self._cache: dict[UUID, frozenset[str]] = {}

    def _check_acyclic(self) -> None:
        for start in self._roles:
            seen: set[UUID] = set()
            cur: UUID | None = start
            while cur is not None:
                if cur in seen:
                    raise ValueError("role hierarchy contains a cycle")
                seen.add(cur)
                cur = self._roles[cur].parent_id

    def effective_permissions(self, role_id: UUID) -> frozenset[str]:
        if role_id in self._cache:
            return self._cache[role_id]
        perms = set(self._roles[role_id].permissions)
        for child in self._children.get(role_id, []):
            perms |= self.effective_permissions(child)
        result = frozenset(perms)
        self._cache[role_id] = result
        return result

    def is_above_or_equal(self, role_id: UUID, other_id: UUID) -> bool:
        cur: UUID | None = other_id
        while cur is not None:
            if cur == role_id:
                return True
            cur = self._roles[cur].parent_id
        return False


def department_subtree(dept_id: UUID, parents: Mapping[UUID, UUID | None]) -> frozenset[UUID]:
    children: dict[UUID, list[UUID]] = defaultdict(list)
    for d, p in parents.items():
        if p is not None:
            children[p].append(d)
    out, stack = set(), [dept_id]
    while stack:
        d = stack.pop()
        if d not in out:
            out.add(d)
            stack.extend(children.get(d, []))
    return frozenset(out)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    needs_second_approval: bool = False
    reason: str = ""


def authorize(
    *,
    graph: RoleGraph,
    perms: Mapping[str, PermissionDef],
    actor_role: UUID,
    actor_is_observer: bool,
    permission: str,
    actor_scope: frozenset[UUID] | None,  # None = global scope
    target_department: UUID | None,
    actor_id: UUID | None = None,
    target_employee_id: UUID | None = None,
    operation: Literal["view", "execute"] = "execute",
) -> Decision:
    """Authorize reads or execution; callers must honor needs_second_approval on execution.

    View is restricted to explicitly marked read permissions, retains scope checks, and
    permits observer visibility without role membership. Execution keeps all normal checks.
    """
    if operation not in ("view", "execute"):
        return Decision(False, reason="unknown_operation")
    pdef = perms.get(permission)
    if pdef is None:
        return Decision(False, reason="unknown_permission")  # fail closed
    observer_visibility = operation == "view" and actor_is_observer and pdef.observer_may_view
    reason = ""
    if operation == "view" and not pdef.observer_may_view:
        reason = "not_view_permission"
    elif permission not in graph.effective_permissions(actor_role) and not observer_visibility:
        reason = "missing_permission"
    elif actor_scope is not None and (
        target_department is None or target_department not in actor_scope
    ):
        reason = "out_of_scope"
    elif operation == "execute" and actor_is_observer and not pdef.observer_may_execute:
        reason = "observer_cannot_execute"
    elif actor_id is not None and actor_id == target_employee_id and pdef.requires_second_approval:
        reason = "self_action_on_sensitive"  # S-014 no self-approval
    if reason:
        return Decision(False, reason=reason)
    return Decision(True, needs_second_approval=pdef.requires_second_approval)
