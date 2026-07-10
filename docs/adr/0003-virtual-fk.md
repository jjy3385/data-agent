# 0003. Virtual Foreign Keys

## Status

Proposed

## Context

Legacy enterprise databases may lack physical foreign keys and often use abbreviated column names or mixed Korean comments.

## Decision

The system will infer and maintain virtual foreign key hints from schema metadata, naming conventions, and database comments.

## Consequences

- Join guidance can improve SQL generation without changing target schemas.
- Inferred relationships must be treated as hints, not trusted facts.
- Virtual FK decisions should be inspectable and auditable.
