# identity

**Owns:** employees, departments, roles (hierarchical, `parent_role_id`), permissions.
**Public API:** `app.modules.identity.api` only.
**Publishes:** `EmployeeRegistered`, `EmployeeApproved` (later: `EmployeeSuspended`, `EmployeeOffboarded`).
**Rules:** registration is always `pending`; approval needs `employee.approve` within scope;
sensitive permissions require a second approver and are never self-applied.

## Least-privilege RBAC

The default role tree is `super_observer → security_lead → department_manager → support → employee`.
`parent_role_id` points upward. Senior roles inherit all descendant permissions; junior roles
never inherit parent permissions. For example, support has `employee.approve` and inherits
`employee.self.view`, but has neither `audit.view` nor `incident.content.remove` unless assigned.

`authorize` and the public `authorize_employee_action` check accept
`operation: Literal["view", "execute"] = "execute"`:

- **View:** only `employee.self.view`, `employee.view`, and `audit.view` are explicitly marked
  `observer_may_view=True`. The Super Observer may view these even without role membership.
  Other actors still require permission membership; department scope applies to everyone.
  Non-read permissions, including sensitive `mailbox.seed.view`, are denied in view mode.
- **Execute (the default):** requires normal role membership and scope. Observer execution
  restrictions, sensitive self-action denial, and second-approval requirements remain in force.
  A successful view check never authorizes execution. Mutating callers must check execute and
  honor `Decision.needs_second_approval` before performing the action.

Visibility metadata is derived from the code catalogue when loading database permissions;
unknown codes default to no observer visibility. No database migration is needed.

**Decision record:** [ADR-006](../../../docs/adr/ADR-006-rbac-least-privilege.md).
**Tests:** `tests/unit/test_rbac.py` (offline policy, repository mapping, and service forwarding).
