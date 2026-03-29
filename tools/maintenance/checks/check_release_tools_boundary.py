#!/usr/bin/env python3
"""Guard release-package versus tools ownership boundaries."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIRS = [
    REPO_ROOT / "src/sage/foundation",
    REPO_ROOT / "src/sage/runtime",
    REPO_ROOT / "src/sage/stream",
    REPO_ROOT / "src/sage/serving",
    REPO_ROOT / "src/sage/edge",
]
RUNTIME_EXTENSIONS = {".py"}
MISPLACED_EXTENSIONS = {".sh", ".bash"}
MISPLACED_SEGMENTS = {"checks", "hooks", "maintenance", "install", "cleanup"}

IMPORT_PATTERNS = [
    (
        "R1",
        "CRITICAL",
        re.compile(r"^\s*(?:from\s+tools(?:\.|\s)|import\s+tools(?:\.|\s|$))"),
        "Release-package runtime code must not import repository-local tools modules.",
        "Move reusable logic into src/sage or call the helper from CLI/maintenance code instead.",
    ),
    (
        "R1",
        "CRITICAL",
        re.compile(r"^\s*(?:from\s+sage\.tools(?:\.|\s)|import\s+sage\.tools(?:\.|\s|$))"),
        "Core runtime layers must not depend on the in-tree developer tools package.",
        "Extract the shared contract into foundation/runtime and keep developer orchestration in sage.tools.",
    ),
]

PATH_PATTERNS = [
    (
        "R2",
        "HIGH",
        re.compile(r"['\"][^'\"]*tools/[^'\"]*['\"]"),
        "Runtime code hard-codes a repository tools path.",
        "Replace the repo-relative tools path with a stable runtime API or configuration value.",
    ),
    (
        "R2",
        "HIGH",
        re.compile(
            r"(?:Path\s*\([^\n]*\)\s*/\s*['\"]tools['\"]|\.joinpath\(\s*['\"]tools['\"]|os\.path\.join\([^\n]*['\"]tools['\"]|subprocess\.(?:run|Popen|call|check_call|check_output)\([^\n]*tools/)"
        ),
        "Runtime code constructs or executes a tools path directly.",
        "Keep repository tooling in maintenance flows and expose a runtime-safe interface if the behavior is required at runtime.",
    ),
]


@dataclass(slots=True)
class Finding:
    rule: str
    severity: str
    path: str
    line: int
    message: str
    suggestion: str


def _run_git(args: list[str]) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _runtime_files() -> list[Path]:
    files: list[Path] = []
    for directory in RUNTIME_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*.py"):
            if any(part == "tests" for part in path.parts):
                continue
            files.append(path)
    return sorted(files)


def _scan_runtime_files() -> list[Finding]:
    findings: list[Finding] = []
    for path in _runtime_files():
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for rule, severity, pattern, message, suggestion in IMPORT_PATTERNS + PATH_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        Finding(
                            rule=rule,
                            severity=severity,
                            path=rel_path,
                            line=line_number,
                            message=message,
                            suggestion=suggestion,
                        )
                    )
    return findings


def _collect_added_files() -> list[str]:
    added = set()
    added.update(_run_git(["diff", "--cached", "--name-only", "--diff-filter=A"]))
    added.update(_run_git(["diff", "--name-only", "--diff-filter=A"]))
    added.update(_run_git(["ls-files", "--others", "--exclude-standard"]))
    return sorted(added)


def _scan_misplaced_new_files() -> list[Finding]:
    findings: list[Finding] = []
    prefixes = (
        "src/sage/foundation/",
        "src/sage/runtime/",
        "src/sage/stream/",
        "src/sage/serving/",
        "src/sage/edge/",
    )
    for rel_path in _collect_added_files():
        if not rel_path.startswith(prefixes):
            continue
        path = Path(rel_path)
        path_text = rel_path.lower()
        if path.suffix in MISPLACED_EXTENSIONS or any(
            segment in MISPLACED_SEGMENTS for segment in path.parts
        ):
            findings.append(
                Finding(
                    rule="R3",
                    severity="MEDIUM",
                    path=rel_path,
                    line=1,
                    message="New file looks like maintenance/install tooling under a runtime-owned package path.",
                    suggestion="Move repository tooling into tools/maintenance or tools/install unless the file is required by a published runtime surface.",
                )
            )
            continue
        if "/checks/" in path_text or "/hooks/" in path_text:
            findings.append(
                Finding(
                    rule="R3",
                    severity="MEDIUM",
                    path=rel_path,
                    line=1,
                    message="New file path introduces checks/hooks semantics under a release package directory.",
                    suggestion="Place repository checks and hooks under tools/maintenance/checks or hooks instead of src/sage runtime layers.",
                )
            )
    return findings


def _print_findings(findings: list[Finding]) -> None:
    for finding in findings:
        print(f"SEVERITY: {finding.severity}")
        print(f"RULE: {finding.rule}")
        print(f"FILE: {finding.path}:{finding.line}")
        print(f"MESSAGE: {finding.message}")
        print(f"SUGGESTION: {finding.suggestion}")
        print()


def _exit_code(findings: list[Finding]) -> int:
    if any(finding.severity in {"CRITICAL", "HIGH"} for finding in findings):
        return 1
    return 0


def main() -> int:
    try:
        findings = _scan_runtime_files()
        findings.extend(_scan_misplaced_new_files())
        findings.sort(key=lambda item: (item.severity, item.path, item.line))
        _print_findings(findings)

        counts = {level: 0 for level in ("CRITICAL", "HIGH", "MEDIUM")}
        for finding in findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1

        result = "FAIL" if _exit_code(findings) else "PASS"
        print(
            "SUMMARY: total={total} critical={critical} high={high} medium={medium}".format(
                total=len(findings),
                critical=counts.get("CRITICAL", 0),
                high=counts.get("HIGH", 0),
                medium=counts.get("MEDIUM", 0),
            )
        )
        print(f"RESULT: {result}")
        return _exit_code(findings)
    except Exception as exc:
        print(f"ERROR: boundary check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
