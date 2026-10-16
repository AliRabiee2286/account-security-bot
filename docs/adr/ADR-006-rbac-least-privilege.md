# ADR-006: Least-privilege RBAC and explicit observer visibility

Status: Accepted, 2026-10-11

## Context

The role hierarchy must give senior roles descendant permissions without granting junior
roles their parents' authority. Super Observer visibility must be explicitly read-only and
must not grant execution of destructive or sensitive actions.

## Decision

The default role tree, from senior to junior, is:

1. `super_observer` (root; owns `audit.view`)
2. `security_lead` (owns `mailbox.seed.view`, `role.assign`, `employee.offboard`)
3. `department_manager` (owns `employee.suspend`, `incident.content.remove`)
4. `support` (owns `employee.view`, `employee.approve`)
5. `employee` (owns `employee.self.view`)

Each level's parent is the preceding level. `parent_role_id` points upward, while
`RoleGraph.effective_permissions` collects a role's own and descendant permissions.
Permissions never flow from a parent to a junior role. Explicit permission assignments are
still supported.

`authorize` and the identity service check expose
`operation: Literal["view", "execute"] = "execute"`:

- `view` authorizes read-only visibility, never execution. Only catalogue permissions with
  `PermissionDef.observer_may_view=True` qualify: `employee.self.view`, `employee.view`, and
  `audit.view`. A Super Observer may view these without permission membership. Non-observers
  still require membership. Scope checks are retained, including denial when a scoped actor
  has no target department. All other permissions are denied in view mode; a `.view` suffix
  alone is insufficient, including sensitive `mailbox.seed.view`.
- `execute` is the backward-compatible default. Permission membership, department scope,
  `observer_may_execute`, sensitive self-action denial, and dual-approval requirements all
  apply. `observer_may_view` never bypasses any execution check. A view decision must never
  be reused to authorize a mutation.
- Unknown permissions and unsupported operation values fail closed.

The identity repository derives the visibility flag from the explicit code catalogue while
preserving database execution and dual-approval flags. Unknown database codes have no
observer visibility; there is no schema change or migration.

## Self-actions and dual approval

Registration remains pending. Employee approval forbids self-approval. For a permission
requiring second approval, an actor targeting themselves is denied with
`self_action_on_sensitive`. For another target, an otherwise allowed execution returns
`Decision(allowed=True, needs_second_approval=True)`: this is eligibility for the approval
workflow, not permission for a single actor to execute immediately. Callers must require
the independent second approval before execution. Observer execution denial is unconditional
for permissions marked `observer_may_execute=False`, even if approval could be obtained.

## Concrete examples

1. Support may approve another pending employee within its department subtree using
   `employee.approve`. Support cannot read `audit.view` or remove incident content through
   inheritance. If explicitly assigned `incident.content.remove`, support still needs a
   second approver and cannot perform that sensitive action on itself.
2. Super Observer may request `employee.view` with `operation="view"` even if the role's
   assignments do not include it, subject to scope. The same absent permission is denied
   for `operation="execute"`. `incident.content.remove` is denied for `operation="view"`
   and denied for observer execution, even when inherited.

## Consequences and verification

The senior-inherits-descendant hierarchy remains intact and existing mutating callers keep
execution semantics. Observer visibility is a narrow, code-reviewed allowlist rather than
a universal read bypass. Tests cover both inheritance directions, explicit assignments,
observer reads versus execution, scope, sensitive self-action, dual approval, unknown codes,
repository metadata parity, and service forwarding without an external database.

Verification commands:

```sh
uv run pytest -q tests/unit/test_rbac.py tests/unit/test_security_primitives.py
python scripts/security_invariants.py
```
