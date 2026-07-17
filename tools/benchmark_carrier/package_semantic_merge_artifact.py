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


def _sanitize(text: str, replacements: list[tuple[str, str]]) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for source, target in replacements:
        count = text.count(source)
        if count:
            text = text.replace(source, target)
            counts[target] = counts.get(target, 0) + count
    private_count = len(PRIVATE_IPV4.findall(text))
    if private_count:
        text = PRIVATE_IPV4.sub("<PRIVATE_IP>", text)
        counts["<PRIVATE_IP>"] = private_count
    return text, counts


def _copy_sanitized(
    source: Path,
    destination: Path,
    replacements: list[tuple[str, str]],
) -> dict[str, Any]:
    data = source.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"submission package only accepts UTF-8 evidence: {source}") from error
    sanitized, counts = _sanitize(text, replacements)
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
        text = path.read_text(encoding="utf-8")
        for source, _ in replacements:
            if source and source in text:
                failures.append(f"identity value remains in {path.relative_to(package_dir)}")
        if PRIVATE_IPV4.search(text):
            failures.append(f"private IP remains in {path.relative_to(package_dir)}")
        if EMAIL.search(text):
            failures.append(f"email address remains in {path.relative_to(package_dir)}")
    return failures


def package(
    comparison_dir: Path,
    endpoint_dir: Path,
    output_dir: Path,
    archive_path: Path | None = None,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    if not comparison_dir.is_dir() or not endpoint_dir.is_dir():
        raise FileNotFoundError("comparison and endpoint inputs must be directories")

    replacements = _replacements()
    files: dict[str, Any] = {}
    for source in sorted(item for item in comparison_dir.rglob("*") if item.is_file()):
        relative = Path("comparison") / source.relative_to(comparison_dir)
        files[str(relative)] = _copy_sanitized(
            source, output_dir / relative, replacements
        )
    for name in ENDPOINT_ALLOWLIST:
        source = endpoint_dir / name
        if not source.is_file():
            raise FileNotFoundError(f"required endpoint evidence is absent: {source}")
        relative = Path("endpoint") / name
        files[str(relative)] = _copy_sanitized(
            source, output_dir / relative, replacements
        )

    readme = output_dir / "README.md"
    readme.write_text(
        "# Anonymous Semantic MapReduce evidence\n\n"
        "This package contains the full comparison matrix and an allowlisted endpoint "
        "provenance slice. Host identity, home paths, and private IPs are replaced; "
        "the manifest preserves source and packaged SHA-256 hashes.\n\n"
        "Verify from the repository root:\n\n"
        "```bash\n"
        "python tools/benchmark_carrier/verify_semantic_merge_artifact.py "
        "comparison --endpoint-metadata endpoint/metadata.json\n"
        "```\n",
        encoding="utf-8",
    )
    files["README.md"] = {
        "source_sha256": None,
        "packaged_sha256": _sha256(readme),
        "replacements": {},
    }

    failures = _audit(output_dir, replacements)
    manifest = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "comparison_source": comparison_dir.name,
        "endpoint_source": endpoint_dir.name,
        "source_roots_redacted": True,
        "endpoint_allowlist": list(ENDPOINT_ALLOWLIST),
        "excluded_endpoint_logs": True,
        "files": files,
    }
    manifest_path = output_dir / "ANONYMIZATION_MANIFEST.json"
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
    args = parser.parse_args()
    result = package(
        args.comparison_dir.resolve(),
        args.endpoint_dir.resolve(),
        args.output_dir.resolve(),
        args.archive.resolve() if args.archive else None,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
