#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import re
import socket
import tarfile
from pathlib import Path
from typing import Any

ENDPOINT_ALLOWLIST = (
    "metadata.json",
    "run-command.env",
    "npu-smi-before.txt",
    "npu-smi-after.txt",
    "npu-smi-current.txt",
    "npu-smi-managed-pids.txt",
)
PRIVATE_IPV4 = re.compile(
    r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
GIT_SHA40 = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", re.IGNORECASE)
GIT_BRANCH = re.compile(
    r"(?:(?:refs/)?heads/)?(?:feature|codex)/[A-Z0-9._/-]+", re.IGNORECASE
)
PUBLIC_GIT_REMOTE = re.compile(
    r"(?:https?://github\.com/|git@github\.com:)[^\s\"']+", re.IGNORECASE
)
SAGE_WORD = re.compile(r"\bsage\b", re.IGNORECASE)
PUBLIC_SYSTEM_NAME = re.compile(r"\bSemantic MapReduce\b", re.IGNORECASE)
IDENTITY_MARKERS = (
    "intellistream",
    "vllm-hust",
    "esage-vllm-hust-dev",
    "VLLM_HUST_API_KEY",
)
REPOSITORY_PATH_REPLACEMENTS = (
    ("external/triton-ascend-hust", "runtime/runtime-component-a"),
    ("external/vllm-ascend-hust", "runtime/runtime-component-b"),
    ("external/vllm-hust-dev-hub", "runtime/runtime-component-d"),
    ("external/vllm-hust", "runtime/runtime-component-c"),
    ("third_party/ascend-runtime-manager", "runtime/runtime-component-e"),
    ("third_party/llm-serving-workloads", "workloads/shared-workloads"),
    ("src/sage/", "src/project/"),
    ("/SAGE", "/PROJECT"),
    ("sage-smr-key-rotation-attestation.json", "key-rotation-attestation.json"),
    ("esage-vllm-hust-dev", "project-specific-env"),
    ("VLLM_HUST_API_KEY", "MODEL_API_KEY"),
    ("qwen25-7b-sage-realonline", "qwen2.5-7b-review-endpoint"),
    ("/data/shared_models/Qwen2.5-7B-Instruct", "<MODEL_PATH>"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _replacements() -> list[tuple[str, str]]:
    home = str(Path.home())
    user = getpass.getuser()
    hostname = socket.gethostname()
    values = [(home, "<USER_HOME>"), (hostname, "<HOSTNAME>"), (user, "<USER>")]
    return sorted((item for item in values if item[0]), key=lambda item: -len(item[0]))


def _discover_revision_replacements(texts: list[str]) -> list[tuple[str, str]]:
    revisions = sorted({match.lower() for text in texts for match in GIT_SHA40.findall(text)})
    replacements: list[tuple[str, str]] = []
    for index, revision in enumerate(revisions, start=1):
        opaque = f"REVISION_{index:03d}"
        replacements.append((revision, opaque))
        # Git describe strings and run IDs commonly retain a 7--12 digit prefix.
        # Replace only prefixes of a full revision found in this package so
        # unrelated numeric fields and 64-character state digests are preserved.
        for length in range(12, 6, -1):
            prefix = revision[:length]
            if sum(item.startswith(prefix) for item in revisions) == 1:
                replacements.append((prefix, opaque))
    return replacements


def _sanitize(
    text: str,
    replacements: list[tuple[str, str]],
    revision_replacements: list[tuple[str, str]],
) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for source, target in revision_replacements:
        count = text.lower().count(source.lower())
        if count:
            text = re.sub(re.escape(source), target, text, flags=re.IGNORECASE)
            counts[target] = counts.get(target, 0) + count
    for source, target in [*REPOSITORY_PATH_REPLACEMENTS, *replacements]:
        count = text.count(source)
        if count:
            text = text.replace(source, target)
            counts[target] = counts.get(target, 0) + count
    branches = GIT_BRANCH.findall(text)
    if branches:
        text = GIT_BRANCH.sub("ANONYMOUS_BRANCH", text)
        counts["ANONYMOUS_BRANCH"] = len(branches)
    remotes = PUBLIC_GIT_REMOTE.findall(text)
    if remotes:
        text = PUBLIC_GIT_REMOTE.sub("<PUBLIC_GIT_REMOTE_REDACTED>", text)
        counts["<PUBLIC_GIT_REMOTE_REDACTED>"] = len(remotes)
    project_names = SAGE_WORD.findall(text)
    if project_names:
        text = SAGE_WORD.sub("PROJECT", text)
        counts["PROJECT"] = len(project_names)
    system_names = PUBLIC_SYSTEM_NAME.findall(text)
    if system_names:
        text = PUBLIC_SYSTEM_NAME.sub("semantic reduction", text)
        counts["semantic reduction"] = len(system_names)
    private_count = len(PRIVATE_IPV4.findall(text))
    if private_count:
        text = PRIVATE_IPV4.sub("<PRIVATE_IP>", text)
        counts["<PRIVATE_IP>"] = private_count
    return text, counts


def _copy_sanitized(
    source: Path,
    destination: Path,
    replacements: list[tuple[str, str]],
    revision_replacements: list[tuple[str, str]],
) -> dict[str, Any]:
    data = source.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"submission package only accepts UTF-8 evidence: {source}") from error
    sanitized, counts = _sanitize(text, replacements, revision_replacements)
    if destination.suffix == ".json":
        try:
            payload = json.loads(sanitized)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            payload["publication_anonymized"] = True
            sanitized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(sanitized, encoding="utf-8")
    return {
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "packaged_sha256": _sha256(destination),
        "replacements": counts,
    }


def _audit(package_dir: Path, replacements: list[tuple[str, str]]) -> list[str]:
    failures: list[str] = []
    for path in sorted(item for item in package_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(package_dir)
        relative_text = str(relative)
        if GIT_SHA40.search(relative_text) or GIT_BRANCH.search(relative_text):
            failures.append(f"Git provenance remains in packaged path {relative}")
        if SAGE_WORD.search(relative_text):
            failures.append(f"repository name remains in packaged path {relative}")
        if PUBLIC_SYSTEM_NAME.search(relative_text):
            failures.append(f"public system name remains in packaged path {relative}")
        for marker in IDENTITY_MARKERS:
            if marker.lower() in relative_text.lower():
                failures.append(
                    f"repository identity marker {marker!r} remains in packaged path {relative}"
                )
        text = path.read_text(encoding="utf-8")
        for source, _ in replacements:
            if source and source in text:
                failures.append(f"identity value remains in {relative}")
        if PRIVATE_IPV4.search(text):
            failures.append(f"private IP remains in {relative}")
        if EMAIL.search(text):
            failures.append(f"email address remains in {relative}")
        if GIT_SHA40.search(text):
            failures.append(f"Git revision remains in {relative}")
        if GIT_BRANCH.search(text):
            failures.append(f"Git branch remains in {relative}")
        if PUBLIC_GIT_REMOTE.search(text):
            failures.append(f"public Git remote remains in {relative}")
        if SAGE_WORD.search(text):
            failures.append(f"repository name remains in {relative}")
        if PUBLIC_SYSTEM_NAME.search(text):
            failures.append(f"public system name remains in {relative}")
        lowered = text.lower()
        for marker in IDENTITY_MARKERS:
            if marker.lower() in lowered:
                failures.append(
                    f"repository identity marker {marker!r} remains in "
                    f"{relative}"
                )
    return failures


def package(
    comparison_dir: Path,
    endpoint_dir: Path,
    output_dir: Path,
    archive_path: Path | None = None,
    supplementary_files: tuple[Path, ...] = (),
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    if not comparison_dir.is_dir() or not endpoint_dir.is_dir():
        raise FileNotFoundError("comparison and endpoint inputs must be directories")

    replacements = _replacements()
    source_files = [
        *sorted(item for item in comparison_dir.rglob("*") if item.is_file()),
        *(endpoint_dir / name for name in ENDPOINT_ALLOWLIST),
        *supplementary_files,
    ]
    source_texts: list[str] = []
    for source in source_files:
        if source.is_file():
            source_texts.append(source.read_text(encoding="utf-8"))
    revision_replacements = _discover_revision_replacements(source_texts)
    files: dict[str, Any] = {}
    for source in sorted(item for item in comparison_dir.rglob("*") if item.is_file()):
        relative = Path("comparison") / source.relative_to(comparison_dir)
        files[str(relative)] = _copy_sanitized(
            source, output_dir / relative, replacements, revision_replacements
        )
    for name in ENDPOINT_ALLOWLIST:
        source = endpoint_dir / name
        if not source.is_file():
            raise FileNotFoundError(f"required endpoint evidence is absent: {source}")
        relative = Path("endpoint") / name
        files[str(relative)] = _copy_sanitized(
            source, output_dir / relative, replacements, revision_replacements
        )
    for source in supplementary_files:
        if not source.is_file():
            raise FileNotFoundError(f"supplementary evidence is absent: {source}")
        relative = Path("supplementary") / source.name
        if str(relative) in files:
            raise ValueError(f"duplicate supplementary filename: {source.name}")
        files[str(relative)] = _copy_sanitized(
            source, output_dir / relative, replacements, revision_replacements
        )

    verification_args = ""
    matrix_manifest = comparison_dir / "matrix" / "manifest.json"
    if matrix_manifest.is_file():
        manifest_payload = json.loads(matrix_manifest.read_text(encoding="utf-8"))
        if len(manifest_payload.get("scenarios", [])) == 9:
            verification_args = (
                " --profile full --min-samples "
                f"{int(manifest_payload.get('samples', 1))}"
            )
    readme = output_dir / "README.md"
    readme.write_text(
        "# Anonymous semantic-reduction evidence\n\n"
        "This package contains the full comparison matrix and an allowlisted endpoint "
        "provenance slice. Identity-bearing paths, Git revisions, branch names, and "
        "repository-specific runtime labels are replaced by consistent opaque labels. "
        "Clean/dirty state and cross-file revision equality remain verifiable. The "
        "manifest preserves source and packaged SHA-256 hashes; exact private provenance "
        "is retained outside this review package.\n\n"
        "Verify from the repository root:\n\n"
        "```bash\n"
        "python tools/benchmark_carrier/verify_semantic_merge_artifact.py "
        "comparison --endpoint-metadata endpoint/metadata.json"
        f"{verification_args}\n"
        "```\n",
        encoding="utf-8",
    )
    files["README.md"] = {
        "source_sha256": None,
        "packaged_sha256": _sha256(readme),
        "replacements": {},
    }

    manifest = {
        "status": "PENDING",
        "failures": [],
        "publication_anonymized": True,
        "comparison_source": "comparison-input",
        "endpoint_source": "endpoint-input",
        "source_roots_redacted": True,
        "git_provenance_redacted": True,
        "endpoint_allowlist": list(ENDPOINT_ALLOWLIST),
        "excluded_endpoint_logs": True,
        "supplementary_files": [path.name for path in supplementary_files],
        "files": files,
    }
    manifest_path = output_dir / "ANONYMIZATION_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    failures = _audit(output_dir, replacements)
    manifest["status"] = "PASS" if not failures else "FAIL"
    manifest["failures"] = failures
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise ValueError("anonymity audit failed: " + "; ".join(failures))

    if archive_path is not None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(output_dir, arcname=output_dir.name)
        manifest["archive"] = str(archive_path)
        manifest["archive_sha256"] = _sha256(archive_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an anonymous, allowlisted Semantic MapReduce artifact package."
    )
    parser.add_argument("--comparison-dir", required=True, type=Path)
    parser.add_argument("--endpoint-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument(
        "--supplementary-file", action="append", default=[], type=Path
    )
    args = parser.parse_args()
    result = package(
        args.comparison_dir.resolve(),
        args.endpoint_dir.resolve(),
        args.output_dir.resolve(),
        args.archive.resolve() if args.archive else None,
        tuple(path.resolve() for path in args.supplementary_file),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
