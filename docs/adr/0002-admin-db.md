# 0002. Admin Database

## Status

Proposed

## Context

The system needs an internal store for users, access policies, audit logs, and error reports without modifying target business databases.

## Decision

Use a separate Admin DB for application metadata and governance records.

## Consequences

- Admin data is isolated from target business data.
- MVP can start with SQLite and evolve later if operational requirements change.
- Audit and error-report workflows depend on Admin DB availability.
