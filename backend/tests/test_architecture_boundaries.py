"""Тесты изоляции слоёв архитектуры (domain, application, persistence)."""

from __future__ import annotations

import ast
from pathlib import Path

CASINO_ROOT = Path(__file__).parents[1] / "casino"


def imported_modules(package: str) -> list[tuple[Path, str]]:
    package_root = CASINO_ROOT / package
    imports: list[tuple[Path, str]] = []
    for source in sorted(package_root.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend((source, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    relative_parent = source.relative_to(CASINO_ROOT).parent.parts
                    package_parts = ("casino", *relative_parent)
                    base = package_parts[: len(package_parts) - node.level + 1]
                    module_parts = tuple(node.module.split(".")) if node.module else ()
                    imported_from = ".".join((*base, *module_parts))
                    if node.module:
                        imports.append((source, imported_from))
                    else:
                        imports.extend(
                            (source, f"{imported_from}.{alias.name}") for alias in node.names
                        )
                elif node.module:
                    imports.append((source, node.module))
    return imports


def test_blackjack_engine_does_not_own_api_or_save_serialization() -> None:
    source = CASINO_ROOT / "domain" / "blackjack.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    blackjack = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Blackjack"
    )
    methods = {
        node.name
        for node in blackjack.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert not methods & {"state", "dump_state", "restore_state"}


def test_domain_records_do_not_own_dictionary_serialization() -> None:
    source = CASINO_ROOT / "domain" / "models.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    records = {"GameResult", "Player"}
    methods = {
        node.name: {
            method.name
            for method in node.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name in records
    }

    assert set(methods) == records
    assert all(not names & {"to_dict", "from_dict"} for names in methods.values())


def test_domain_does_not_depend_on_application_or_adapters() -> None:
    forbidden = (
        "casino.application",
        "casino.persistence",
        "casino.errors",
        "fastapi",
        "sqlite3",
    )
    violations = [
        f"{source.relative_to(CASINO_ROOT)} imports {module}"
        for source, module in imported_modules("domain")
        if any(
            module == dependency or module.startswith(dependency + ".") for dependency in forbidden
        )
    ]
    assert violations == []


def test_application_does_not_depend_on_transport_or_persistence_adapter() -> None:
    forbidden = (
        "casino.persistence",
        "casino.api",
        "casino.api_schemas",
        "casino.errors",
        "fastapi",
        "sqlite3",
    )
    violations = [
        f"{source.relative_to(CASINO_ROOT)} imports {module}"
        for source, module in imported_modules("application")
        if any(
            module == dependency or module.startswith(dependency + ".") for dependency in forbidden
        )
    ]
    assert violations == []


def test_canonical_packages_do_not_import_root_compatibility_errors() -> None:
    violations = [
        f"{source.relative_to(CASINO_ROOT)} imports {module}"
        for package in ("domain", "application", "persistence")
        for source, module in imported_modules(package)
        if module == "casino.errors"
    ]
    assert violations == []


def test_persistence_ports_do_not_expose_database_handles() -> None:
    ports = CASINO_ROOT / "application" / "ports.py"
    tree = ast.parse(ports.read_text(encoding="utf-8"), filename=str(ports))
    imported = {
        alias.name if isinstance(node, ast.Import) else node.module
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "sqlite3" not in imported
    assert not any(isinstance(node, ast.Name) and node.id == "Any" for node in ast.walk(tree))
    assert not any(
        isinstance(node, ast.arg) and node.arg in {"db", "connection"} for node in ast.walk(tree)
    )
