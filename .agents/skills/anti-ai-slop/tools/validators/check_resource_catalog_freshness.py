from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from tools.resource_catalog_freshness import check as check_resource_catalog
    from .common import Finding, run_cli
except ImportError:
    from tools.resource_catalog_freshness import check as check_resource_catalog
    from common import Finding, run_cli


def check(root: Path) -> list[Finding]:
    return check_resource_catalog(root)


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Resource Catalog Freshness Check"))
