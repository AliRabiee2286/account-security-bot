# ADR-005: Evidence-based release gates

Status: Accepted, 2026-10-09

A phase is not complete because code exists or syntax compiles. Completion requires reproducible
runtime evidence in disposable staging, named reviewers, and the exact gate output stored with
the project. Static checks may pass while runtime gates remain blocked.

Phase 1 requires: empty-database migration, CI checks, PostgreSQL/Redis integration, concurrent
one-time consume and outbox claim tests, webhook smoke, encrypted backup restore, and security
review. Phase 2 additionally requires signed Telegram Mini App proof, AuthContext approval,
WebAuthn ceremony, and session issuance only after approval and MFA.
