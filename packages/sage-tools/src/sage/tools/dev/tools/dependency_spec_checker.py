"""Dependency spec consistency checker.

Validates that package ``pyproject.toml`` dependency pins match the unified
``dependencies-spec.yaml`` at the repository root.

This is a lightweight parser that avoids adding a YAML dependency by parsing
the simple ``key: "specifier"`` format used in the spec file.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover - fallback for older interpreters
    import tomli as tomllib


class DependencyMismatch(Exception):
    """Raised when dependency versions do not match the unified spec."""


def _load_spec(spec_path: Path) -> dict[str, SpecifierSet]:
    if not spec_path.exists():
        raise FileNotFoundError(
            f"dependencies-spec.yaml not found at {spec_path}. "
            "Please create it before running the check."
        )

    spec: dict[str, SpecifierSet] = {}
    for raw_line in spec_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            spec[key.lower()] = SpecifierSet(value)
    return spec


def _iter_pyprojects(packages_dir: Path) -> Iterable[Path]:
    for pyproject in packages_dir.glob("*/pyproject.toml"):
        if pyproject.is_file():
            yield pyproject


def _collect_requirements(pyproject: Path) -> list[Requirement]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    requirements: list[Requirement] = []

    project = data.get("project", {})
    deps = project.get("dependencies", []) or []
    requirements.extend(_to_requirements(deps))

    optional = project.get("optional-dependencies", {}) or {}
    for extra_deps in optional.values():
        requirements.extend(_to_requirements(extra_deps))

    return requirements


def _to_requirements(items: Iterable[str]) -> list[Requirement]:
    reqs: list[Requirement] = []
    for item in items:
        if not isinstance(item, str):
            continue
        try:
            reqs.append(Requirement(item))
        except Exception:
            # Ignore unparsable entries to avoid breaking the whole check
            continue
    return reqs


def check_dependencies_spec(project_root: Path) -> dict[str, list[str]]:
    """Check all packages against the unified dependency spec.

    Returns a mapping of package name to list of human-readable mismatch messages.
    """

    spec_path = project_root / "dependencies-spec.yaml"
    spec = _load_spec(spec_path)

    packages_dir = project_root / "packages"
    if not packages_dir.exists():
        raise FileNotFoundError(f"packages directory not found at {packages_dir}")

    mismatches: dict[str, list[str]] = defaultdict(list)

    for pyproject in _iter_pyprojects(packages_dir):
        pkg_name = pyproject.parent.name
        requirements = _collect_requirements(pyproject)

        for req in requirements:
            name = req.name.lower()
            if name not in spec:
                continue
            desired = spec[name]
            if req.specifier != desired:
                mismatches[pkg_name].append(
                    f"{req.name}: found '{req.specifier}' but spec requires '{desired}'"
                )

    return mismatches


def assert_dependencies_match(project_root: Path) -> None:
    mismatches = check_dependencies_spec(project_root)
    if not mismatches:
        return

    lines: list[str] = ["Dependency versions do not match dependencies-spec.yaml:"]
    for pkg, issues in sorted(mismatches.items()):
        lines.append(f"- {pkg}:")
        for issue in issues:
            lines.append(f"  - {issue}")
    raise DependencyMismatch("\n".join(lines))
