# 0004. Agent Workflow Depth Limit

## Status

Proposed

## Context

Multi-step reasoning can help with practical business questions, but uncontrolled agent loops increase latency, cost, and operational risk.

## Decision

Agentic workflows will be limited to a maximum depth of 2 during MVP.

## Consequences

- Complex tasks must be decomposed conservatively.
- The system avoids unbounded planning and execution loops.
- Some advanced investigations may require follow-up questions or post-MVP expansion.
