from __future__ import annotations

import tempfile
import unittest
from importlib import import_module
from pathlib import Path

from tools.validators import check_architecture_boundaries
from tools.validators import check_all
from tools.validators import check_dependency_justification
from tools.validators import check_glossary_terms
from tools.validators import check_task_traceability
from tools.validators.common import iter_text_files


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ValidatorCoreTests(unittest.TestCase):
    def test_traceability_finds_missing_requirement_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / ".specify/memory/constitution.md", "# Constitution\n")
            write(root / ".specify/memory/glossary.md", "| Term | Meaning |\n|---|---|\n| AI slop | Quality failure |\n| AI-smell risk | Risk |\n| output contract | Contract |\n| evidence-to-revision | Trace |\n")
            write(root / ".specify/memory/architecture-principles.md", "tools/validators/\n.specify/\ncodex/prompts/\n.agents/skills/\ndocs/process/\n")
            write(root / ".specify/memory/product-principles.md", "# Product\n")
            write(root / "codex/prompts/00-apply-pack-to-existing-repo.md", "# Apply\n")
            write(root / "codex/prompts/01-run-coherence-check.md", "# Check\n")
            write(root / "codex/prompts/02-pr-review.md", "# Review\n")
            write(root / "specs/demo/spec.md", "# Spec\n\n- FR-001: Do a thing.\n\n## Out of Scope\n\n- None.\n")
            write(root / "specs/demo/plan.md", "# Plan\n")
            write(root / "specs/demo/tasks.md", "# Tasks\n\n- [ ] T001 Missing reference.\n")

            findings = check_all.check(root)

            self.assertTrue(any(f.rule == "task-traceability" and f.severity == "HIGH" for f in findings))

    def test_dependency_checker_treats_future_and_importlib_as_stdlib(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "tools/demo.py", "from __future__ import annotations\nimport importlib\nimport json\nimport traceback\n")
            findings = check_dependency_justification.check(root)
            self.assertEqual([], [f for f in findings if f.severity == "HIGH"])

    def test_dependency_checker_allows_baseline_imports_and_flags_new_imports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "dependency-baseline.json", '{"schema_version": 1, "python_imports": ["requests"], "manifests": []}\n')
            write(root / "tools/baseline.py", "import requests\n")
            write(root / "tools/new_dep.py", "import httpx\n")

            findings = check_dependency_justification.check(root)
            messages = "\n".join(f.message for f in findings)

            self.assertNotIn("`requests`", messages)
            self.assertIn("`httpx`", messages)

    def test_dependency_checker_reports_invalid_baseline_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "dependency-baseline.json", "{bad json")

            findings = check_dependency_justification.check(root)

            self.assertTrue(
                any(
                    f.rule == "dependency-justification"
                    and f.severity == "HIGH"
                    and "dependency-baseline.json" in f.path
                    for f in findings
                )
            )

    def test_text_file_scan_skips_repo_state_not_codex_parent_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".codex" / "skills" / "pack"
            write(root / "README.md", "# Visible\n")
            write(root / ".codex/review-driven-development/state.md", "# State\n")

            scanned = {path.relative_to(root).as_posix() for path in iter_text_files(root.resolve())}

            self.assertIn("README.md", scanned)
            self.assertNotIn(".codex/review-driven-development/state.md", scanned)

    def test_architecture_checker_does_not_flag_read_only_string_literals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / ".specify/memory/architecture-principles.md", "tools/validators/\n.specify/\ncodex/prompts/\n.agents/skills/\ndocs/process/\n")
            write(root / "tools/validators/demo.py", "MUTATION_TOKENS = ['write_text(', 'unlink(']\n")
            findings = check_architecture_boundaries.check(root)
            self.assertEqual([], [f for f in findings if f.severity == "HIGH"])

    def test_glossary_checker_normalizes_required_term_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / ".specify/memory/glossary.md", "| Term | Meaning |\n|---|---|\n| AI slop | Quality failure |\n| AI-smell risk | Risk |\n| Output contract | Contract |\n| Evidence-to-revision | Trace |\n")
            findings = check_glossary_terms.check(root)
            self.assertEqual([], [f for f in findings if f.rule == "glossary-terms" and "misses required" in f.message])

    def test_check_all_reports_checker_crashes_as_critical_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_checks = check_all.CHECKS
            check_all.CHECKS = ["validator_that_does_not_exist"]
            try:
                findings = check_all.check(root)
            finally:
                check_all.CHECKS = original_checks

            self.assertTrue(
                any(
                    f.rule == "CHECK_CRASH"
                    and f.severity == "CRITICAL"
                    and "validator_that_does_not_exist" in f.message
                    for f in findings
                )
            )

    def test_check_all_reports_invalid_guardrails_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "config/guardrails.json", "{bad json")
            findings = check_all.check(root)
            self.assertTrue(
                any(
                    f.rule == "config-integrity"
                    and f.severity == "CRITICAL"
                    and "guardrails.json" in f.path
                    for f in findings
                )
            )

    def test_check_all_reports_manifest_integrity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "manifest.txt",
                "README.md\n"
                "docs/references/resource-catalog.yaml\n"
                "stale.md\n",
            )
            write(root / "README.md", "# Readme\n")
            write(root / "extra.md", "# Extra\n")
            write(
                root / "docs/references/resource-catalog.yaml",
                "resources:\n"
                "  - name: example\n"
                "    verified_at: 2026-06-25\n"
                "    maintenance_status: active\n"
                "    license_checked: true\n",
            )

            findings = check_all.check(root)
            messages = "\n".join(f.message for f in findings if f.rule == "manifest-integrity")

            self.assertIn("extra.md", messages)
            self.assertIn("stale.md", messages)

    def test_check_all_feature_profile_scopes_findings_to_selected_feature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "specs/target/spec.md", "# Spec\n\n- FR-001: Target.\n\n## Out of Scope\n\n- None.\n")
            write(root / "specs/target/plan.md", "# Plan\n")
            write(root / "specs/target/tasks.md", "# Tasks\n\n- [ ] T001 [FR-001] Implement target.\n")
            write(root / "specs/other/spec.md", "# Spec\n\n- FR-001: Other.\n\n## Out of Scope\n\n- None.\n")
            write(root / "specs/other/plan.md", "# Plan\n")
            write(root / "specs/other/tasks.md", "# Tasks\n\n- [ ] T001 Missing reference.\n")

            pack_findings = check_all.check(root, profile="pack-self")
            feature_findings = check_all.check(root, profile="feature", feature="target")

            self.assertTrue(any(f.path == "specs/other/tasks.md" for f in pack_findings))
            self.assertEqual([], [f for f in feature_findings if f.path.startswith("specs/other/")])
            self.assertEqual([], [f for f in feature_findings if f.severity in {"CRITICAL", "HIGH"}])

    def test_check_all_rejects_unknown_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                check_all.check(Path(tmp), profile="unknown")

    def test_current_repo_check_all_has_no_blocking_findings(self) -> None:
        root = Path(__file__).resolve().parents[1]
        findings = check_all.check(root.resolve())
        blocking = [f for f in findings if f.severity in {"CRITICAL", "HIGH"}]
        self.assertEqual([], blocking)

    def test_config_integrity_rejects_nested_yaml_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "config/guardrails.yaml",
                "profiles:\n"
                "  pack-self:\n"
                "    include_dirs: [tools]\n",
            )
            check_config_integrity = import_module("tools.validators.check_config_integrity")

            findings = check_config_integrity.check(root)
            self.assertTrue(
                any(
                    f.rule == "config-integrity"
                    and f.severity == "CRITICAL"
                    and "Nested YAML" in f.message
                    for f in findings
                )
            )

    def test_config_integrity_rejects_local_overlay_until_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "config/guardrails.local.json", "{}\n")
            check_config_integrity = import_module("tools.validators.check_config_integrity")

            findings = check_config_integrity.check(root)

            self.assertTrue(
                any(
                    f.rule == "config-integrity"
                    and f.severity == "HIGH"
                    and "guardrails.local.json" in f.path
                    and "not supported" in f.message
                    for f in findings
                )
            )

    def test_task_traceability_ignores_fenced_task_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "specs/demo/spec.md", "# Spec\n\n- FR-001: Do a thing.\n\n## Out of Scope\n\n- None.\n")
            write(
                root / "specs/demo/tasks.md",
                "# Tasks\n\n"
                "```md\n"
                "- T001 Improve dashboard\n"
                "- T002 Refactor backend\n"
                "```\n\n"
                "- [ ] T003 [FR-001] Implement the thing.\n",
            )

            findings = check_task_traceability.check(root)

            self.assertEqual([], [f for f in findings if f.severity == "HIGH"])

    def test_template_token_checker_flags_shipped_template_tokens_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / ".specify/templates/overrides/spec-template.md", "Path: specs/[###-feature-name]/spec.md\n")
            write(root / "specs/demo/spec.md", "Path: specs/[###-feature-name]/spec.md\n")
            check_template_tokens = import_module("tools.validators.check_template_tokens")

            findings = check_template_tokens.check(root)

            self.assertEqual(["specs/demo/spec.md"], [f.path for f in findings])
            self.assertTrue(all(f.rule == "template-tokens" and f.severity == "HIGH" for f in findings))

    def test_evidence_link_checker_flags_missing_paths_and_allows_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "specs/demo/tasks.md",
                "# Tasks\n\n"
                "- [x] T001 [FR-001] Done. Evidence: `specs/demo/evidence/missing.md`\n"
                "- [ ] T002 [FR-001] Later. Evidence: Pending until implementation\n",
            )
            check_evidence_links = import_module("tools.validators.check_evidence_links")

            findings = check_evidence_links.check(root)

            self.assertEqual(1, len(findings))
            self.assertEqual("evidence-links", findings[0].rule)
            self.assertEqual("HIGH", findings[0].severity)
            self.assertIn("missing.md", findings[0].message)

    def test_task_traceability_catches_reverse_orphan_width_and_parallel_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "specs/demo/spec.md",
                "# Spec\n\n"
                "- FR-001: First requirement.\n"
                "- FR-002: Orphan requirement.\n"
                "- US-001: User story.\n"
                "- SC-001: Success criterion.\n"
                "\n## Out of Scope\n\n- None.\n",
            )
            write(root / "specs/demo/plan.md", "# Plan\n\nADR-001: Accepted design.\n")
            write(
                root / "specs/demo/tasks.md",
                "# Tasks\n\n"
                "- [ ] T001 [FR-001] [US-999] [SC-999] [ADR-999] Files: a.py, b.py, c.py, d.py, e.py, f.py\n"
                "- [ ] T002 [P] [FR-001] Files: shared.py\n"
                "- [ ] T003 [P] [FR-001] Files: shared.py\n",
            )

            findings = check_task_traceability.check(root)
            messages = "\n".join(f.message for f in findings)

            self.assertIn("FR-002 is not referenced", messages)
            self.assertIn("missing US references: US-999", messages)
            self.assertIn("missing SC references: SC-999", messages)
            self.assertIn("missing ADR references: ADR-999", messages)
            self.assertIn("touches 6 files without an ADR", messages)
            self.assertIn("Parallel tasks share files", messages)


if __name__ == "__main__":
    unittest.main()
