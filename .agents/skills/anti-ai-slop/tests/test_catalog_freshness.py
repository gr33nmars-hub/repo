from __future__ import annotations

import tempfile
import unittest
from importlib import import_module
from pathlib import Path


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CatalogFreshnessTests(unittest.TestCase):
    def test_resource_catalog_freshness_reports_missing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "docs/references/resource-catalog.yaml",
                "resources:\n"
                "  - name: example\n"
                "    type: documentation\n"
                "    url: https://example.test/docs\n"
                "    use: example source\n",
            )
            resource_catalog_freshness = import_module("tools.resource_catalog_freshness")

            findings = resource_catalog_freshness.check(root)
            messages = "\n".join(f.message for f in findings)

            self.assertIn("verified_at", messages)
            self.assertIn("maintenance_status", messages)
            self.assertIn("license_checked", messages)

    def test_check_all_includes_resource_catalog_freshness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "docs/references/resource-catalog.yaml",
                "resources:\n"
                "  - name: example\n"
                "    type: documentation\n"
                "    url: https://example.test/docs\n"
                "    use: example source\n",
            )
            check_all = import_module("tools.validators.check_all")

            findings = check_all.check(root)

            self.assertTrue(any(f.rule == "resource-catalog-freshness" for f in findings))


if __name__ == "__main__":
    unittest.main()
