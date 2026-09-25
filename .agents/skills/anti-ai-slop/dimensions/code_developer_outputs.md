# Dimension Review: Code and Developer Outputs

Use for generated code, scripts, frontend components, backend snippets, PR drafts, technical explanations, API integrations, and developer documentation.

## Purpose

Code should work in the target environment, respect local assumptions, and fail safely. Clean-looking code is not enough.

## Common generic patterns

| Pattern | Visible sign | Risk |
|---|---|---|
| Happy-path only | Handles one ideal input | Breaks in production |
| Hardcoded values | URLs, tokens, IDs, limits, sample data embedded | Security and maintainability risk |
| Generic error handling | `catch (error) { console.log(error) }` or one broad error | Hides real failure modes |
| Hallucinated API | Nonexistent method, package, option, or outdated syntax | Runtime failure |
| Boilerplate repetition | Similar functions or validation copied repeatedly | Increases bug surface |
| Surface-level comments | Comments explain syntax, not business logic | Creates noise without understanding |
| Missing tests | No tests or only success tests | Edge cases remain unknown |
| Weak integration fit | Ignores auth, permissions, rate limits, data shape, deployment constraints | Fails outside demo |
| Prompt/scaffold residue | “As an AI,” TODO placeholders, copied boilerplate, sample users, fake IDs, unfilled env names | Signals the code was not adapted to the target system |
| Security theater | Comments or docs claim privacy/security without validation, permissions, retention, encryption, or audit behavior | Creates false confidence |

## Review checklist

- What runtime, framework, version, and environment does this target?
- What inputs are valid, empty, malformed, large, or unauthorized?
- What external services, files, credentials, or network calls are assumed?
- Are errors typed or at least distinguishable?
- Are secrets excluded from code?
- Are tests included for failure paths?
- Are accessibility and responsive behavior checked for frontend code?
- Are security risks considered for user input, file handling, auth, and database access?
- Are demo-only placeholders, generated scaffold comments, and fake sample data removed or clearly isolated?
- Do security/privacy claims correspond to implemented behavior?

## Repair patterns

### Replace placeholders

```text
Weak: const API_KEY = "sk-...";
Better: Read API key from environment and fail with a clear configuration error if missing.
```

### Add validation

Check:

- required fields;
- type and range;
- empty arrays and strings;
- null and undefined;
- unexpected enum values;
- maximum size;
- permission and ownership.

### Improve errors

Use errors that distinguish:

- invalid input;
- missing configuration;
- unauthorized access;
- rate limit;
- upstream service failure;
- timeout;
- not found;
- conflict;
- unknown internal error.

### Add tests

Minimum test set:

- one success case;
- one invalid input case;
- one missing configuration case;
- one upstream failure case;
- one boundary or large-input case;
- one unauthorized or permission case when relevant.

## Frontend-specific checks

- Loading, empty, error, success, disabled, selected, and permission states exist.
- Keyboard navigation works.
- Focus states are visible.
- Color is not the only indicator.
- Long text and small screens are handled.
- Mock data is clearly marked and removable.

## Acceptance criteria

- The code states its environment assumptions.
- It handles realistic failure modes.
- It contains no secrets or production placeholders.
- APIs and dependencies are version-compatible or flagged for verification.
- Tests or validation steps cover more than the happy path.
