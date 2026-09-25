# ADR 0001: Use Standard-Library Validators

## Status

Accepted

## Context

The guardrail pack needs executable coherence checks that can run in a fresh Codex environment without package installation.

## Decision

Implement validators with Python standard-library modules only. Keep optional external scanners in the resource catalog and GitHub Actions examples, not in the required local validator path.

## Consequences

- Local validation is easy to run.
- Checks are conservative and text-oriented.
- More advanced semantic analysis can be added later only with explicit dependency justification.
