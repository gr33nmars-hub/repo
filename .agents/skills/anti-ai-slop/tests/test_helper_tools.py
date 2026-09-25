from __future__ import annotations

import json
import subprocess
import shutil
import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path

from tools.validators import check_all


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class HelperToolTests(unittest.TestCase):
    def test_bootstrap_feature_replaces_path_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / ".specify/templates/overrides/spec-template.md",
                "Feature: [FEATURE NAME]\nPath: specs/[###-feature-name]/spec.md\nFiles: specs/[feature]/evidence/scan.md\n",
            )
            bootstrap_feature = import_module("tools.bootstrap_feature")

            created = bootstrap_feature.bootstrap(root, "123-demo-feature", "Demo Feature", "Ship the demo")

            spec_text = (root / "specs/123-demo-feature/spec.md").read_text(encoding="utf-8")
            self.assertIn(root / "specs/123-demo-feature/spec.md", created)
            self.assertNotIn("[###-feature-name]", spec_text)
            self.assertNotIn("[feature]", spec_text)
            self.assertIn("specs/123-demo-feature/spec.md", spec_text)
            self.assertIn("specs/123-demo-feature/evidence/scan.md", spec_text)

    def test_bootstrapped_feature_passes_aggregate_validators(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(repo_root / ".specify", root / ".specify")
            shutil.copytree(repo_root / "codex", root / "codex")
            shutil.copytree(repo_root / "docs/references", root / "docs/references")
            bootstrap_feature = import_module("tools.bootstrap_feature")

            bootstrap_feature.bootstrap(root, "123-demo-feature", "Demo Feature", "Ship the demo")
            findings = check_all.check(root)

            self.assertEqual([], [f for f in findings if f.severity in {"CRITICAL", "HIGH"}])

    def test_apply_guardrails_dry_run_does_not_create_missing_target(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "missing-target"
            write(source / ".specify/memory/constitution.md", "# Constitution\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "dry-run",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("copy .specify/memory/constitution.md", result.stdout)
            self.assertFalse(target.exists())

    def test_apply_guardrails_dry_run_refuses_target_contained_report_outputs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "missing-target"
            write(source / ".specify/memory/constitution.md", "# Constitution\n")

            for option, filename in (
                ("--manifest-out", ".anti-ai-slop-apply-manifest.json"),
                ("--json-out", "dry-run-report.json"),
            ):
                with self.subTest(option=option):
                    report_path = target / filename
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(repo_root / "tools/apply_guardrails.py"),
                            "--source",
                            str(source),
                            "--target",
                            str(target),
                            "--mode",
                            "dry-run",
                            option,
                            str(report_path),
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("Dry-run report output cannot be inside the target repository", result.stderr)
                    self.assertFalse(target.exists())
                    self.assertFalse(report_path.exists())

    def test_apply_guardrails_merge_writes_manifest_and_preserves_existing_files(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            manifest = target / ".anti-ai-slop-apply-manifest.json"
            write(source / "VERSION", "9.8.7\n")
            write(source / ".specify/memory/constitution.md", "# Source Constitution\n")
            write(source / ".specify/memory/glossary.md", "# Glossary\n")
            write(target / ".specify/memory/constitution.md", "# Target Constitution\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "merge",
                    "--manifest-out",
                    str(manifest),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("# Target Constitution\n", (target / ".specify/memory/constitution.md").read_text(encoding="utf-8"))
            self.assertEqual("# Glossary\n", (target / ".specify/memory/glossary.md").read_text(encoding="utf-8"))
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(1, data["schema_version"])
            self.assertEqual("apply_guardrails", data["tool"])
            self.assertEqual("9.8.7", data["tool_version"])
            self.assertIn("created_at", data)
            self.assertEqual("merge", data["mode"])
            self.assertTrue(data["changed"])
            self.assertIn("skip existing .specify/memory/constitution.md", data["actions"])
            self.assertIn("copy .specify/memory/glossary.md", data["actions"])

    def test_apply_guardrails_refuses_to_overwrite_existing_manifest(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            manifest = target / ".anti-ai-slop-apply-manifest.json"
            write(source / ".specify/memory/constitution.md", "# Constitution\n")
            write(target / "README.md", "# Target\n")
            write(manifest, "{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "merge",
                    "--manifest-out",
                    str(manifest),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("Manifest already exists", result.stderr)

    def test_apply_guardrails_ignores_generated_cache_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            write(source / "tools/apply_guardrails.py", "print('tool')\n")
            write(source / "tools/__pycache__/apply_guardrails.cpython-313.pyc", "bytecode\n")
            write(source / "tools/.pytest_cache/CACHEDIR.TAG", "cache\n")
            write(target / "README.md", "# Target\n")

            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "dry-run",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, dry_run.returncode, dry_run.stderr)
            self.assertIn("copy tools/apply_guardrails.py", dry_run.stdout)
            self.assertNotIn("__pycache__", dry_run.stdout)
            self.assertNotIn(".pytest_cache", dry_run.stdout)

            merge = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "merge",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, merge.returncode, merge.stderr)
            self.assertTrue((target / "tools/apply_guardrails.py").exists())
            self.assertFalse((target / "tools/__pycache__/apply_guardrails.cpython-313.pyc").exists())
            self.assertFalse((target / "tools/.pytest_cache/CACHEDIR.TAG").exists())

    def test_apply_guardrails_uses_manifest_pack_surface(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            write(
                source / "manifest.txt",
                "\n".join(
                    [
                        "AGENTS.md",
                        ".github/workflows/spec-coherence.yml",
                        "VERSION",
                        "CHANGELOG.md",
                        "dependency-baseline.json",
                        "README.md",
                        "SKILL.md",
                        "manifest.txt",
                        "tools/apply_guardrails.py",
                        "tests/test_helper_tools.py",
                        "tools/__pycache__/apply_guardrails.cpython-313.pyc",
                        "",
                    ]
                ),
            )
            for rel in (
                "AGENTS.md",
                ".github/workflows/spec-coherence.yml",
                "VERSION",
                "CHANGELOG.md",
                "dependency-baseline.json",
                "README.md",
                "SKILL.md",
                "tools/apply_guardrails.py",
                "tests/test_helper_tools.py",
                "tools/__pycache__/apply_guardrails.cpython-313.pyc",
            ):
                write(source / rel, f"{rel}\n")
            write(target / "README.md", "# Existing target README\n")

            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "dry-run",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, dry_run.returncode, dry_run.stderr)
            self.assertIn("copy AGENTS.md", dry_run.stdout)
            self.assertIn("copy .github/workflows/spec-coherence.yml", dry_run.stdout)
            self.assertIn("copy VERSION", dry_run.stdout)
            self.assertIn("copy CHANGELOG.md", dry_run.stdout)
            self.assertIn("copy dependency-baseline.json", dry_run.stdout)
            self.assertIn("copy manifest.txt", dry_run.stdout)
            self.assertIn("skip existing README.md", dry_run.stdout)
            self.assertNotIn("tests/test_helper_tools.py", dry_run.stdout)
            self.assertNotIn("__pycache__", dry_run.stdout)

            merge = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "merge",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, merge.returncode, merge.stderr)
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertTrue((target / ".github/workflows/spec-coherence.yml").exists())
            self.assertTrue((target / "VERSION").exists())
            self.assertTrue((target / "dependency-baseline.json").exists())
            self.assertTrue((target / "manifest.txt").exists())
            self.assertEqual("# Existing target README\n", (target / "README.md").read_text(encoding="utf-8"))
            self.assertFalse((target / "tests/test_helper_tools.py").exists())
            self.assertFalse((target / "tools/__pycache__/apply_guardrails.cpython-313.pyc").exists())

    def test_apply_guardrails_reports_missing_manifest_entries(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            report = root / "report.json"
            write(source / "manifest.txt", "AGENTS.md\nmissing.md\n")
            write(source / "AGENTS.md", "# Agents\n")
            write(target / "README.md", "# Target\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "dry-run",
                    "--json-out",
                    str(report),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("copy AGENTS.md", result.stdout)
            self.assertIn("missing manifest entry missing.md", result.stderr)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertIn("missing manifest entry missing.md", data["warnings"])

    def test_apply_guardrails_manifest_is_authoritative_even_when_entries_are_missing(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            write(source / "manifest.txt", "missing.md\n")
            write(source / ".specify/memory/constitution.md", "# Constitution\n")
            write(target / "README.md", "# Target\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--mode",
                    "dry-run",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("missing manifest entry missing.md", result.stderr)
            self.assertNotIn(".specify/memory/constitution.md", result.stdout)

    def test_apply_guardrails_applied_target_passes_target_repo_gate(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            manifest = target / ".anti-ai-slop-apply-manifest.json"
            write(target / "README.md", "# Target\n")

            apply_result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/apply_guardrails.py"),
                    "--source",
                    str(repo_root),
                    "--target",
                    str(target),
                    "--mode",
                    "merge",
                    "--manifest-out",
                    str(manifest),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, apply_result.returncode, apply_result.stderr)
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertTrue((target / "tools/validators/check_all.py").exists())
            self.assertTrue(manifest.exists())

            check_result = subprocess.run(
                [
                    sys.executable,
                    str(target / "tools/validators/check_all.py"),
                    "--root",
                    str(target),
                    "--profile",
                    "target-repo",
                    "--format",
                    "markdown",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, check_result.returncode, check_result.stdout + check_result.stderr)
            self.assertIn("Score: 100", check_result.stdout)

    def test_repo_inventory_scans_codex_parent_root_and_skips_repo_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".codex" / "skills" / "pack"
            write(root / "README.md", "# Readme\n")
            write(root / "tools/demo.py", "print('demo')\n")
            write(root / ".codex/review-driven-development/state.md", "# State\n")
            repo_inventory = import_module("tools.repo_inventory")

            files = {path.relative_to(root).as_posix() for path in repo_inventory.iter_files(root.resolve())}

            self.assertIn("README.md", files)
            self.assertIn("tools/demo.py", files)
            self.assertNotIn(".codex/review-driven-development/state.md", files)

    def test_repo_inventory_json_output_is_machine_readable(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".codex" / "skills" / "pack"
            out = Path(tmp) / "inventory.json"
            write(root / "README.md", "# Readme\n")
            write(root / "tools/demo.py", "print('demo')\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "tools/repo_inventory.py"),
                    "--root",
                    str(root),
                    "--format",
                    "json",
                    "--out",
                    str(out),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(2, data["file_count"])
            self.assertEqual("present", data["priority_files"]["README.md"])
            self.assertEqual(1, data["top_directories"]["tools"])


if __name__ == "__main__":
    unittest.main()
