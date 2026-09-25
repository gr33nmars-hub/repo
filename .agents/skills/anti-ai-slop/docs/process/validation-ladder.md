# Validation Ladder

| Level | Check | Evidence |
|---|---|---|
| L1 | Inventory | `tools/repo_inventory.py` output |
| L2 | Static coherence | `tools/validators/check_all.py` report |
| L3 | Project tests | Existing test command output |
| L4 | Reviewer pass | PR review findings and decisions |
| L5 | Release gate | Security/dependency scan summaries |

Escalate only when lower levels reveal missing evidence or high-risk changes.
