# ADR-002: Incident removal is approval-gated

Status: Accepted by project owner, 2026-10-08

## Decision

A scanner creates evidence and a severity finding. It never deletes content. A human reviews
the incident, and a sensitive removal action requires two independent approvals. The action may
only use an official platform API whose capability is documented for that platform/account type.
If the platform cannot remove the content, notify the employee and create a deadline; do not use
scraping, password login, MTProto user sessions, or browser automation.

## Why

False positives are an operational and legal risk. Platform capabilities differ: X owned-post
delete is possible, Instagram post/story deletion is not documented in the current API, and a
Telegram Bot cannot control a user's personal posts/stories.

## Consequences

The system is slower than a reckless auto-delete bot, but reversible, auditable, and compliant
with the project's security and consent decisions. Incident status is `open -> acknowledged ->
removal_pending -> secured/resolved`; every transition is in the append-only audit log.
