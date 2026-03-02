#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LAYER_RE = re.compile(r"\b(L[1-6])\b")
WORKSPACE_ENTRY_RE = re.compile(
    r'\{[^{}]*?"name"\s*:\s*"([^"]+)"[^{}]*?"path"\s*:\s*"([^"]+)"[^{}]*?\}',
    flags=re.S,
)


def _extract_layer_token(raw: str) -> str | None:
    match = LAYER_RE.search(raw)
    return match.group(1) if match else None


def load_manifest(path: Path) -> tuple[dict[str, str], set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    repos = data.get("repos", [])
    optional_repos = set(data.get("declaration_optional_repos", []))
    mapping: dict[str, str] = {}
    for item in repos:
        repo = item["repo"]
        layer = item["layer"]
        mapping[repo] = layer
    return mapping, optional_repos


def load_workspace_labels(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    mapping: dict[str, str] = {}
    for name, rel_path in WORKSPACE_ENTRY_RE.findall(text):
        layer = _extract_layer_token(name)
        if layer is None:
            continue
        repo = Path(rel_path).name
        mapping[repo] = layer
    return mapping


def load_declared_layer(instructions_path: Path) -> str | None:
    text = instructions_path.read_text(encoding="utf-8", errors="ignore")

    match = re.search(r"Layer\s*:\s*\*\*([^*]+)\*\*", text)
    if match:
        return _extract_layer_token(match.group(1))

    match = re.search(r"Layer\s+L[1-6][^\n]*", text)
    if match:
        return _extract_layer_token(match.group(0))

    return None


def run_check(
    repo_root: Path, workspace_file: Path, manifest_file: Path, strict_repos: bool
) -> int:
    manifest, optional_declaration_repos = load_manifest(manifest_file)
    workspace = load_workspace_labels(workspace_file)

    errors: list[str] = []
    warnings: list[str] = []

    for repo, expected_layer in manifest.items():
        workspace_layer = workspace.get(repo)
        if workspace_layer is None:
            errors.append(
                f"[workspace-missing] {repo}: not found in {workspace_file.relative_to(repo_root)}"
            )
        elif workspace_layer != expected_layer:
            errors.append(
                f"[workspace-layer-mismatch] {repo}: workspace={workspace_layer}, expected={expected_layer}"
            )

        if repo in optional_declaration_repos:
            continue

        repo_instructions = repo_root.parent / repo / ".github" / "copilot-instructions.md"
        if not repo_instructions.exists():
            msg = f"[instructions-missing] {repo}: {repo_instructions} does not exist"
            if strict_repos:
                errors.append(msg)
            else:
                warnings.append(msg)
            continue

        declared_layer = load_declared_layer(repo_instructions)
        if declared_layer is None:
            msg = (
                f"[instructions-layer-missing] {repo}: "
                f"no parseable Layer declaration in {repo_instructions}"
            )
            if strict_repos:
                errors.append(msg)
            else:
                warnings.append(msg)
            continue

        if declared_layer != expected_layer:
            errors.append(
                f"[instructions-layer-mismatch] {repo}: declared={declared_layer}, expected={expected_layer}"
            )

    if warnings:
        print("⚠️ Layer manifest consistency warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("❌ Layer manifest consistency check failed:")
        for err in errors:
            print(f"  - {err}")
        print("\nFix order: repo copilot instructions -> layer-manifest -> SAGE.code-workspace")
        return 1

    print("✅ Layer manifest consistency check passed")
    print(f"   checked repos: {len(manifest)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check layer consistency across manifest/workspace/repo declarations"
    )
    parser.add_argument(
        "--workspace",
        default="SAGE.code-workspace",
        help="Workspace file path relative to repo root",
    )
    parser.add_argument(
        "--manifest",
        default="packages/sage/docs/layer-manifest.json",
        help="Layer manifest path relative to repo root",
    )
    parser.add_argument(
        "--strict-repos",
        action="store_true",
        help="Treat missing/unparseable satellite repo instructions as errors",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    workspace_file = repo_root / args.workspace
    manifest_file = repo_root / args.manifest

    if not workspace_file.exists():
        print(f"❌ Workspace file not found: {workspace_file}")
        return 2
    if not manifest_file.exists():
        print(f"❌ Manifest file not found: {manifest_file}")
        return 2

    return run_check(
        repo_root=repo_root,
        workspace_file=workspace_file,
        manifest_file=manifest_file,
        strict_repos=args.strict_repos,
    )


if __name__ == "__main__":
    sys.exit(main())
