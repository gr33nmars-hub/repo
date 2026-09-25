# Apply Anti-AI Slop Guardrail Pack To Existing Repo

Use this prompt in the target repository.

```text
Apply the anti-ai-slop Spec Kit guardrail pack to this existing repository.

Workflow:
1. Inventory the repo.
2. Read .specify/memory/constitution.md, glossary.md, architecture-principles.md, and product-principles.md.
3. Create or update a feature spec before implementation.
4. Clarify missing output contract details only when needed.
5. Create checklist, plan, and tasks with requirement traceability.
6. Implement the smallest complete slice.
7. Run tools/validators/check_all.py and project tests.
8. Record validation evidence and PR review notes.

Constraints:
- Preserve existing code unless a traceable requirement justifies replacement.
- Do not make AI authorship claims.
- Do not add dependencies without justification.
```
