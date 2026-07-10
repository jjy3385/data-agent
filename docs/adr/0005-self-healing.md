# 0005. SQL Self-Healing Limit

## Status

Proposed

## Context

Generated SQL may fail due to schema ambiguity, invalid joins, or dialect issues. Automatic retry can improve usefulness, but repeated regeneration can hide unsafe behavior.

## Decision

If SQL execution fails, the system may attempt at most one self-healing regeneration, and the regenerated SQL must pass the same guardrails again.

## Consequences

- Retry behavior is predictable and bounded.
- Guardrails remain mandatory after regeneration.
- Persistent failures should be logged and surfaced rather than repeatedly retried.
