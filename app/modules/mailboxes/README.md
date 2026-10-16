# mailboxes

Owns mailbox lifecycle and assignment history. Provider calls are adapters and run in workers.
`request_provision` records a pending request only; it never blocks Telegram on proof-of-work.
Recovery secrets are sealed with the KeyProvider immediately and never returned in DTOs.
