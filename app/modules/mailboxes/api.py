from app.modules.mailboxes.schemas import MailboxDTO, MailboxRequest
from app.modules.mailboxes.service import get_active_owned_mailbox, request_provision

__all__ = ["MailboxDTO", "MailboxRequest", "get_active_owned_mailbox", "request_provision"]
