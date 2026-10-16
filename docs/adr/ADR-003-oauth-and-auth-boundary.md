# ADR-003: OAuth PKCE and fail-closed authentication boundary

Status: Proposed, 2026-10-09

OAuth uses Authorization Code + PKCE. State, verifier, and tokens are never sent through
Telegram or stored in URLs. State is stored hashed and consumed once; scopes are allowlisted
per provider; issuer, audience, exact redirect URI, and token response schema are validated.

Every privileged endpoint receives an `AuthContext` from the authentication boundary. It never
accepts an employee ID from JSON. Until Telegram-linked sessions and phishing-resistant MFA are
implemented, the boundary returns unavailable and the endpoint returns 503. This is intentional:
secure downtime beats an impersonation bug.
