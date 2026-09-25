from __future__ import annotations

import unittest
from pathlib import Path


class TestLayoutTests(unittest.TestCase):
    def test_tests_are_split_by_domain(self) -> None:
        root = Path(__file__).resolve().parent
        expected = [
            "test_validator_core.py",
            "test_workflow_examples.py",
            "test_helper_tools.py",
            "test_catalog_freshness.py",
        ]

        missing = [name for name in expected if not (root / name).exists()]
        self.assertEqual([], missing)

    def test_release_metadata_is_present_and_documented(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = (root / "manifest.txt").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")
        skill = (root / "SKILL.md").read_text(encoding="utf-8")

        self.assertRegex((root / "VERSION").read_text(encoding="utf-8").strip(), r"^\d+\.\d+\.\d+$")
        self.assertIn("## 0.", (root / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn("VERSION", manifest)
        self.assertIn("CHANGELOG.md", manifest)
        self.assertIn("Update `VERSION`", readme)
        self.assertIn("CHANGELOG.md", readme)
        self.assertIn("VERSION", skill)
        self.assertIn("CHANGELOG.md", skill)

    def test_docs_describe_current_guardrail_surface(self) -> None:
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        required_terms = [
            "check_config_integrity.py",
            "check_evidence_links.py",
            "check_template_tokens.py",
            "check_workflow_integrity.py",
            "resource_catalog_freshness.py",
            "dependency-baseline.json",
            "config/guardrails.json",
            "config/guardrails.yaml",
            "--profile",
            "--manifest-out",
        ]

        for term in required_terms:
            self.assertIn(term, readme)
            self.assertIn(term, skill)
        self.assertNotIn("There is no JSON config", readme)

    def test_readme_documents_multi_agent_usage_and_static_workflow(self) -> None:
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        manifest = (root / "manifest.txt").read_text(encoding="utf-8")

        for term in [
            "### Claude Code",
            ".claude\\skills\\anti-ai-slop",
            "CLAUDE.md",
            "### Other Agent Runtimes",
            "assets/workflow.svg",
            "## Actual Logs",
            "python tools\\validators\\check_all.py",
            "python tools\\repo_inventory.py",
            "python tools\\apply_guardrails.py",
        ]:
            self.assertIn(term, readme)

        self.assertIn("CLAUDE.md", manifest)
        self.assertIn("assets/workflow.svg", manifest)
        self.assertNotIn("assets/readme-demo.gif", manifest)
        self.assertNotIn("tools/generate_readme_demo_gif.py", manifest)


if __name__ == "__main__":
    unittest.main()
