"""Base errors. user_message is Persian and safe to show; details go to logs only."""

from __future__ import annotations


class AppError(Exception):
    code = "app_error"
    user_message = "خطایی رخ داد. لطفاً دوباره تلاش کنید."

    def __init__(self, detail: str = "", **context: object) -> None:
        super().__init__(detail or self.code)
        self.detail = detail
        self.context = context


class PermissionDenied(AppError):
    code = "permission_denied"
    user_message = "شما مجوز انجام این کار را ندارید."


class NotFound(AppError):
    code = "not_found"
    user_message = "مورد درخواستی پیدا نشد."


class ValidationFailed(AppError):
    code = "validation_failed"
    user_message = "اطلاعات واردشده معتبر نیست."


class RateLimited(AppError):
    code = "rate_limited"
    user_message = "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید."  # noqa: RUF001 - intentional Persian user-facing text


class ApprovalRequired(AppError):
    code = "approval_required"
    user_message = "این کار نیاز به تأیید نفر دوم دارد."
