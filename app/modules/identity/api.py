"""Public contract of the identity module (D-009 rule 1). Import only from here."""

from app.modules.identity import permissions
from app.modules.identity.events import EmployeeApproved, EmployeeRegistered
from app.modules.identity.schemas import EmployeeDTO, RegisterRequest
from app.modules.identity.service import (
    approve,
    authorize_employee_action,
    find_active_by_telegram,
    get_active_employee,
    register,
)

__all__ = [
    "EmployeeApproved",
    "EmployeeDTO",
    "EmployeeRegistered",
    "RegisterRequest",
    "approve",
    "authorize_employee_action",
    "find_active_by_telegram",
    "get_active_employee",
    "permissions",
    "register",
]
