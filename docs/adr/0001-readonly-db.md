# 0001. Read-Only Target Database Access

## Status

Proposed

## Context

The agent queries enterprise data sources through generated SQL. Target databases must be protected from mutation, accidental writes, and unsafe execution paths.

## Decision

Target database access will be read-only by default.

## Consequences

- Application credentials must not have write privileges on target databases.
- Generated SQL must pass guardrails before execution.
- Any uncertainty in query safety must fail closed.
