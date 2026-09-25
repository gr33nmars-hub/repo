# Run Coherence Check

```text
Run the anti-ai-slop coherence validators for this repo.

Commands:
python tools/repo_inventory.py --root . --out specs/_meta/evidence/existing-code-scan.md
python tools/validators/check_all.py --root . --format markdown --out specs/_meta/coherence-latest.md

Summarize:
- score
- critical/high findings
- unresolved requirements
- next fix
```
