#!/usr/bin/env python3
"""Fail commits that reintroduce local/embedded inference paths.

Looks for added lines in staged diffs that match forbidden control-plane bypass
patterns. Add `# allow-control-plane-bypass` to intentionally permit a line.
"""

from __future__ import annotations

import re
import subprocess
import sys

FORBIDDEN_PATTERNS: dict[str, re.Pattern[str]] = {
    "embedded": re.compile(r"embedded\s*=\s*True"),  # allow-control-plane-bypass
    "prefer_local": re.compile(r"prefer_local\s*="),  # allow-control-plane-bypass
    "detect_llm": re.compile(r"_detect_llm_endpoint"),  # allow-control-plane-bypass
    "detect_embed": re.compile(r"_detect_embedding_endpoint"),  # allow-control-plane-bypass
    "hardcoded_gateway_port": re.compile(r"http://localhost:8888"),  # allow-control-plane-bypass
    "hardcoded_llm_port": re.compile(r"http://localhost:800[01]"),  # allow-control-plane-bypass
}

ALLOW_TAG = "allow-control-plane-bypass"


def main() -> int:
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--cached", "-U0", "--no-color"],
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Failed to read staged diff: {exc}", file=sys.stderr)
        return 1

    violations: list[str] = []
    current_file: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[len("+++ b/") :]
            continue
        # Skip scanning the guard script itself
        if current_file == "tools/hooks/check_control_plane_only.py":
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if ALLOW_TAG in line:
            continue
        content = line[1:]
        for name, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(content):
                rel = current_file or "<unknown>"
                violations.append(f"{rel}: forbids {name}: {content.strip()}")
                break

    if violations:
        print(
            "❌ Control-plane-only guard triggered. Remove local/embedded paths or add"
            f" `{ALLOW_TAG}` if intentional."
        )
        for v in violations:
            print(f"  - {v}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
