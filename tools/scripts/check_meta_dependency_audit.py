#!/usr/bin/env python3
"""Dependency audit gate for isage meta package.

This gate enforces two rules for `pyproject.toml`:
1. Every direct dependency must have callsite evidence in the audit document.
2. When dependency declarations change, the audit document must be updated in the same change.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = Path("pyproject.toml")
AUDIT_DOC_PATH = Path("docs/dependency-audit-gate.md")

SECTION_RE = re.compile(r"^###\s+`([^`]+)`\s*$")
CALLSITE_RE = re.compile(r"^-\s+Callsite:\s+")
REQ_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def _run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def _dependency_name(requirement: str) -> str:
    match = REQ_NAME_RE.match(requirement.strip())
    if not match:
        raise ValueError(f"Cannot parse dependency name from requirement: {requirement}")
    return match.group(1).lower()


def _load_dependency_map_from_text(pyproject_text: str) -> dict[str, str]:
    data = tomllib.loads(pyproject_text)
    deps = data.get("project", {}).get("dependencies", [])
    result: dict[str, str] = {}
    for req in deps:
        name = _dependency_name(req)
        result[name] = req.strip()
    return result


def _load_current_dependency_map() -> dict[str, str]:
    text = (REPO_ROOT / PYPROJECT_PATH).read_text(encoding="utf-8")
    return _load_dependency_map_from_text(text)


def _load_base_dependency_map(refspec: str | None) -> dict[str, str]:
    if refspec:
        base_ref = refspec.split("...")[0] if "..." in refspec else refspec
        base_sha = _run_git(["merge-base", base_ref, "HEAD"]).stdout.strip()
        if not base_sha:
            return {}
        show = _run_git(["show", f"{base_sha}:{PYPROJECT_PATH.as_posix()}"], check=False)
        if show.returncode != 0:
            return {}
        return _load_dependency_map_from_text(show.stdout)

    show_head = _run_git(["show", f"HEAD:{PYPROJECT_PATH.as_posix()}"], check=False)
    if show_head.returncode != 0:
        return {}
    return _load_dependency_map_from_text(show_head.stdout)


def _changed_files(refspec: str | None, staged: bool) -> set[str]:
    args = ["diff", "--name-only"]
    if staged:
        args.append("--cached")
    if refspec:
        args.append(refspec)
    result = _run_git(args, check=False)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _diff_text(path: Path, refspec: str | None, staged: bool) -> str:
    args = ["diff"]
    if staged:
        args.append("--cached")
    if refspec:
        args.append(refspec)
    args.extend(["--", path.as_posix()])
    result = _run_git(args, check=False)
    return result.stdout if result.returncode == 0 else ""


def _parse_audit_doc() -> dict[str, bool]:
    doc_path = REPO_ROOT / AUDIT_DOC_PATH
    if not doc_path.exists():
        raise FileNotFoundError(f"Audit document not found: {AUDIT_DOC_PATH.as_posix()}")

    sections: dict[str, bool] = {}
    current_dep: str | None = None

    for raw_line in doc_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        sec_match = SECTION_RE.match(line)
        if sec_match:
            current_dep = sec_match.group(1).lower()
            sections[current_dep] = False
            continue

        if current_dep and CALLSITE_RE.match(line):
            sections[current_dep] = True

    return sections


def _dependency_delta(
    base_deps: dict[str, str], current_deps: dict[str, str]
) -> dict[str, tuple[str, str]]:
    all_names = set(base_deps) | set(current_deps)
    delta: dict[str, tuple[str, str]] = {}
    for name in sorted(all_names):
        base_req = base_deps.get(name, "")
        current_req = current_deps.get(name, "")
        if base_req != current_req:
            delta[name] = (base_req, current_req)
    return delta


def _ensure_doc_covers_dependencies(current_deps: dict[str, str]) -> list[str]:
    sections = _parse_audit_doc()
    errors: list[str] = []
    for dep_name in sorted(current_deps):
        if dep_name not in sections:
            errors.append(f"Missing section: ### `{dep_name}` in {AUDIT_DOC_PATH.as_posix()}")
        elif not sections[dep_name]:
            errors.append(
                f"Section `{dep_name}` has no `- Callsite:` evidence in {AUDIT_DOC_PATH.as_posix()}"
            )
    return errors


def _ensure_change_has_evidence(
    delta: dict[str, tuple[str, str]],
    changed_files: set[str],
    refspec: str | None,
    staged: bool,
) -> list[str]:
    errors: list[str] = []
    if not delta:
        return errors

    pyproject_changed = PYPROJECT_PATH.as_posix() in changed_files
    if not pyproject_changed:
        return errors

    audit_changed = AUDIT_DOC_PATH.as_posix() in changed_files
    if not audit_changed:
        errors.append(
            "Dependency declarations changed but audit doc was not updated: "
            f"{AUDIT_DOC_PATH.as_posix()}"
        )
        return errors

    doc_diff = _diff_text(AUDIT_DOC_PATH, refspec=refspec, staged=staged)
    added_lines = [
        line[1:]
        for line in doc_diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    added_blob = "\n".join(added_lines).lower()

    missing_names = [name for name in delta if name.lower() not in added_blob]
    if missing_names:
        errors.append(
            "Audit doc updated, but changed dependencies are not explicitly mentioned in added lines: "
            + ", ".join(missing_names)
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check isage meta dependency audit gate")
    parser.add_argument(
        "--enforce-change-evidence",
        action="store_true",
        help="Require audit doc update when dependencies change",
    )
    parser.add_argument(
        "--refspec",
        default=None,
        help="Git diff refspec (e.g. origin/main-dev...HEAD)",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Use staged changes (`git diff --cached`) for change detection",
    )
    args = parser.parse_args()

    current_deps = _load_current_dependency_map()
    base_deps = _load_base_dependency_map(args.refspec)
    delta = _dependency_delta(base_deps, current_deps)
    changed_files = _changed_files(refspec=args.refspec, staged=args.staged)

    errors: list[str] = []
    errors.extend(_ensure_doc_covers_dependencies(current_deps))

    if args.enforce_change_evidence:
        errors.extend(
            _ensure_change_has_evidence(
                delta=delta,
                changed_files=changed_files,
                refspec=args.refspec,
                staged=args.staged,
            )
        )

    if errors:
        print("❌ isage meta dependency audit gate failed:")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("✅ isage meta dependency audit gate passed")
    if delta:
        print(f"ℹ️ Dependency delta detected: {', '.join(sorted(delta))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
