"""Permission catalogue (seeded into DB by migration; code references these constants)."""

from app.modules.identity.rbac import PermissionDef

EMPLOYEE_SELF_VIEW = "employee.self.view"
EMPLOYEE_VIEW = "employee.view"
EMPLOYEE_APPROVE = "employee.approve"
EMPLOYEE_SUSPEND = "employee.suspend"
EMPLOYEE_OFFBOARD = "employee.offboard"
ROLE_ASSIGN = "role.assign"
AUDIT_VIEW = "audit.view"
SEED_VIEW = "mailbox.seed.view"
CONTENT_REMOVE = "incident.content.remove"

CATALOGUE: dict[str, PermissionDef] = {
    p.code: p
    for p in [
        PermissionDef(EMPLOYEE_SELF_VIEW, observer_may_view=True),
        PermissionDef(EMPLOYEE_VIEW, observer_may_view=True),
        PermissionDef(EMPLOYEE_APPROVE),
        PermissionDef(EMPLOYEE_SUSPEND, observer_may_execute=False),
        PermissionDef(EMPLOYEE_OFFBOARD, requires_second_approval=True, observer_may_execute=False),
        PermissionDef(ROLE_ASSIGN, requires_second_approval=True, observer_may_execute=False),
        PermissionDef(AUDIT_VIEW, observer_may_view=True),
        PermissionDef(SEED_VIEW, requires_second_approval=True, observer_may_execute=False),
        PermissionDef(CONTENT_REMOVE, requires_second_approval=True, observer_may_execute=False),
    ]
}

# Default role skeleton (D-007: exact levels decided later; structure is ready now).
# code -> (parent_code, own permissions)
DEFAULT_ROLES: dict[str, tuple[str | None, list[str]]] = {
    "super_observer": (None, [AUDIT_VIEW]),
    "security_lead": ("super_observer", [SEED_VIEW, ROLE_ASSIGN, EMPLOYEE_OFFBOARD]),
    "department_manager": ("security_lead", [EMPLOYEE_SUSPEND, CONTENT_REMOVE]),
    "support": ("department_manager", [EMPLOYEE_VIEW, EMPLOYEE_APPROVE]),
    "employee": ("support", [EMPLOYEE_SELF_VIEW]),
}
