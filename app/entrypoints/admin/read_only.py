"""SQLAdmin policy: Phase 5 exposes masked, read-only views first.

No credential/seed/token columns are registered. Mutations remain service-only and require
RBAC + dual approval. This module is a policy placeholder until SQLAdmin is installed.
"""

READ_ONLY_MODELS = ("Employee", "Mailbox", "SocialAccount", "Incident", "AuditEvent")
FORBIDDEN_FIELDS = frozenset({"password", "seed", "token", "secret", "ciphertext", "wrapped_dek"})
