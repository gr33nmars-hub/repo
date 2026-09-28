"""Canonical game-rule metadata stored alongside completed rounds."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def fingerprint_rules(version: str, snapshot: dict[str, Any]) -> str:
    """Hash a stable JSON representation of a versioned rule snapshot."""
    canonical = json.dumps(
        {"version": version, "rules": snapshot},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_rule_metadata(
    version: str | None,
    fingerprint: str | None,
    snapshot: dict[str, Any] | None,
    outcome: dict[str, Any] | None,
) -> None:
    """Reject partial, malformed, or mismatched provenance while accepting old rounds."""
    if version is fingerprint is snapshot is outcome is None:
        return
    if type(version) is not str or not version:
        raise ValueError("Game rule version is invalid")
    if type(snapshot) is not dict or type(outcome) is not dict:
        raise ValueError("Versioned game results require rules and outcome objects")
    if type(fingerprint) is not str or len(fingerprint) != 64:
        raise ValueError("Game rule fingerprint is invalid")
    if any(character not in "0123456789abcdef" for character in fingerprint):
        raise ValueError("Game rule fingerprint is invalid")
    try:
        actual = fingerprint_rules(version, snapshot)
        json.dumps(outcome, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("Game rule metadata is not valid JSON") from error
    if actual != fingerprint:
        raise ValueError("Game rule snapshot does not match its fingerprint")
