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
LOOPBACK_ENDPOINT = re.compile(r"\b(?:https?://)?127\.0\.0\.1:\d{2,5}\b")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PORT_FIELD = re.compile(r"(?i)([\"']?\bport\b[\"']?\s*[:=]\s*[\"']?)\d{2,5}")
PID_FIELD = re.compile(r"(?i)([\"']?\b(?:pid|process_id|main_pid)\b[\"']?\s*[:=]\s*[\"']?)\d+")
UNIT_CONTAINER_FIELD = re.compile(
    r"(?i)((?:[\"']?(?:systemd_unit|managed_unit|container)[\"']?)\s*[:=]\s*[\"']?)([^\s,\"']+)"
)
PCI_BUS_ID = re.compile(r"\b[0-9A-Fa-f]{4}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}\.[0-9A-Fa-f]\b")
NPU_PROCESS_ROW = re.compile(r"(?m)^(\|\s*\d+\s+\d+\s+\|)\s*\d+\s*(\|)")
NPU_MANAGED_PID_ROW = re.compile(r"(?m)^(\s*\d+\s+)\d+(\s*)$")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
GIT_SHA40 = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", re.IGNORECASE)
GIT_REVISION_TOKEN = re.compile(
    r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])", re.IGNORECASE
)
GIT_BRANCH = re.compile(
    r"(?:(?:refs/)?heads/)?(?:feature|codex)/[A-Z0-9._/-]+", re.IGNORECASE
)
PUBLIC_GIT_REMOTE = re.compile(
    r"(?:https?://github\.com/|git@github\.com:)[^\s\"']+", re.IGNORECASE
)
GIT_DESCRIBE = re.compile(
    r"\b[A-Z0-9][A-Z0-9._-]*-\d+-g(?:[0-9a-f]{7,40}|REVISION_\d{3})\b",
    re.IGNORECASE,
)
SAGE_WORD = re.compile(r"\bsage\b", re.IGNORECASE)
PUBLIC_SYSTEM_NAME = re.compile(r"\bSemantic MapReduce\b", re.IGNORECASE)
PUBLICATION_ARCHIVE_ROOT = "artifact"
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
    ("qwen25-14b-sage-eurosys27", "qwen2.5-14b-review-endpoint"),
    ("/data/shared_models/Qwen--Qwen2.5-14B-Instruct", "<MODEL_PATH>"),
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
    text, describe_count = GIT_DESCRIBE.subn("<GIT_DESCRIBE>", text)
    if describe_count:
        counts["<GIT_DESCRIBE>"] = describe_count
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
    loopback_count = len(LOOPBACK_ENDPOINT.findall(text))
    if loopback_count:
        text = LOOPBACK_ENDPOINT.sub("<LOCAL_ENDPOINT>", text)
        counts["<LOCAL_ENDPOINT>"] = loopback_count
    text, ip_count = IPV4.subn("<IP_ADDRESS>", text)
    if ip_count:
        counts["<IP_ADDRESS>"] = ip_count
    text, port_count = PORT_FIELD.subn(r"\1<PORT>", text)
    if port_count:
        counts["<PORT>"] = port_count
    text, pid_count = PID_FIELD.subn(r"\1<PID>", text)
    if pid_count:
        counts["<PID>"] = pid_count
    text, service_count = UNIT_CONTAINER_FIELD.subn(r"\1<SCOPED_SERVICE>", text)
    if service_count:
        counts["<SCOPED_SERVICE>"] = service_count
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
    if destination.name.startswith("npu-smi-"):
        sanitized, pci_count = PCI_BUS_ID.subn("<PCI_BUS_ID>", sanitized)
        sanitized, process_count = NPU_PROCESS_ROW.subn(r"\1 <PID> \2", sanitized)
        if destination.name == "npu-smi-managed-pids.txt":
            sanitized, managed_count = NPU_MANAGED_PID_ROW.subn(r"\1<PID>\2", sanitized)
            process_count += managed_count
        if pci_count:
            counts["<PCI_BUS_ID>"] = pci_count
        if process_count:
            counts["<PID>"] = process_count
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


def _audit(
    package_dir: Path,
    replacements: list[tuple[str, str]],
    revision_replacements: list[tuple[str, str]] = (),
) -> list[str]:
    failures: list[str] = []
    for path in sorted(item for item in package_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(package_dir)
        relative_text = str(relative)
        if GIT_REVISION_TOKEN.search(relative_text) or GIT_BRANCH.search(relative_text):
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
        if LOOPBACK_ENDPOINT.search(text) or IPV4.search(text) or PORT_FIELD.search(text):
            failures.append(f"endpoint or port remains in {relative}")
        if PID_FIELD.search(text):
            failures.append(f"process ID remains in {relative}")
        if any(match.group(2) != "<SCOPED_SERVICE>" for match in UNIT_CONTAINER_FIELD.finditer(text)):
            failures.append(f"unit or container remains in {relative}")
        if PCI_BUS_ID.search(text):
            failures.append(f"PCI bus identifier remains in {relative}")
        if relative.parts[:1] == ("endpoint",) and relative.name.startswith("npu-smi-"):
            if NPU_PROCESS_ROW.search(text) or (
                relative.name == "npu-smi-managed-pids.txt"
                and NPU_MANAGED_PID_ROW.search(text)
            ):
                failures.append(f"process ID remains in {relative}")
        if EMAIL.search(text):
            failures.append(f"email address remains in {relative}")
        # Arbitrary 7--40 character hexadecimal strings in report content can
        # legitimately be timestamps, request IDs, or state digests.  Content
        # auditing therefore checks only revisions (and their unambiguous
        # prefixes) discovered from the source package.  Paths remain stricter:
        # caller-controlled archive/output names must never expose a short SHA.
        lowered_text = text.lower()
        if any(source.lower() in lowered_text for source, _ in revision_replacements):
            failures.append(f"Git revision remains in {relative}")
        if GIT_BRANCH.search(text):
            failures.append(f"Git branch remains in {relative}")
        if PUBLIC_GIT_REMOTE.search(text):
            failures.append(f"public Git remote remains in {relative}")
        if GIT_DESCRIBE.search(text):
            failures.append(f"Git describe remains in {relative}")
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
    supplementary_dirs: tuple[tuple[str, Path], ...] = (),
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    if not comparison_dir.is_dir() or not endpoint_dir.is_dir():
        raise FileNotFoundError("comparison and endpoint inputs must be directories")

    replacements = _replacements()
    bundled_verifier = Path(__file__).with_name("verify_semantic_merge_artifact.py")
    if not bundled_verifier.is_file():
        raise FileNotFoundError(f"bundled verifier is absent: {bundled_verifier}")
    source_files = [
        *sorted(item for item in comparison_dir.rglob("*") if item.is_file()),
        *(endpoint_dir / name for name in ENDPOINT_ALLOWLIST),
        *supplementary_files,
        *(
            source
            for _, directory in supplementary_dirs
            for source in sorted(item for item in directory.rglob("*") if item.is_file())
        ),
    ]
    source_texts: list[str] = []
    for source in source_files:
        if source.is_file():
            source_texts.append(source.read_text(encoding="utf-8"))
    revision_replacements = _discover_revision_replacements(source_texts)
    files: dict[str, Any] = {}
    files["verify.py"] = _copy_sanitized(
        bundled_verifier,
        output_dir / "verify.py",
        replacements,
        revision_replacements,
    )
    environment = output_dir / "environment.json"
    environment.write_text(
        json.dumps(
            {
                "publication_anonymized": True,
                "python": ">=3.11",
                "dependencies": "Python standard library only",
                "entrypoint": "verify.py",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    files["environment.json"] = {
        "source_sha256": None,
        "packaged_sha256": _sha256(environment),
        "replacements": {},
    }
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
    for label, directory in supplementary_dirs:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", label):
            raise ValueError(f"unsafe supplementary directory label: {label!r}")
        if not directory.is_dir():
            raise FileNotFoundError(f"supplementary evidence directory is absent: {directory}")
        for source in sorted(item for item in directory.rglob("*") if item.is_file()):
            relative = Path("supplementary") / label / source.relative_to(directory)
            if str(relative) in files:
                raise ValueError(f"duplicate supplementary path: {relative}")
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
    supplementary_inventory = ""
    if supplementary_dirs or supplementary_files:
        directory_lines = "".join(
            f"- `supplementary/{label}/`\n" for label, _ in supplementary_dirs
        )
        file_lines = "".join(
            f"- `supplementary/{path.name}`\n" for path in supplementary_files
        )
        supplementary_inventory = (
            "\n## Supplementary evidence\n\n"
            + directory_lines
            + file_lines
            + "\nEvidence labels and scope fields in these files are normative. In "
            "particular, `real-online`, `replay`, and `derived-artifact` must not "
            "be conflated. A label-conditioned reducer replay is not an end-to-end "
            "detection result, and a second model scale in one family is not "
            "cross-family robustness.\n"
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
        "Verify from the extracted package root with Python 3.11 or newer; the "
        "verifier uses only the Python standard library:\n\n"
        "```bash\n"
        "python verify.py "
        "comparison --endpoint-metadata endpoint/metadata.json"
        f"{verification_args}\n"
        "```\n\n"
        "With no `--output`, verification is read-only and writes only to stdout. "
        "If a report file is desired, choose a fresh path outside the extracted package.\n\n"
        "Verify package integrity and provenance redaction with "
        "`ANONYMIZATION_MANIFEST.json`; every packaged file has a SHA-256 entry "
        "and the manifest must report `status=PASS`, an empty `failures` list, "
        "and `publication_anonymized=true`.\n"
        + supplementary_inventory,
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
        "supplementary_dirs": [label for label, _ in supplementary_dirs],
        "files": files,
    }
    manifest_path = output_dir / "ANONYMIZATION_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    failures = _audit(output_dir, replacements, revision_replacements)
    manifest["status"] = "PASS" if not failures else "FAIL"
    manifest["failures"] = failures
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise ValueError("anonymity audit failed: " + "; ".join(failures))

    if archive_path is not None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "w:gz") as archive:
            # The local output directory may contain a timestamp or private Git
            # revision. Never preserve that caller-controlled name in the
            # double-blind archive.
            archive.add(output_dir, arcname=PUBLICATION_ARCHIVE_ROOT)
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
    parser.add_argument(
        "--supplementary-dir",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="Add a recursively packaged evidence directory under a safe opaque label.",
    )
    args = parser.parse_args()
    supplementary_dirs: list[tuple[str, Path]] = []
    for item in args.supplementary_dir:
        if "=" not in item:
            parser.error("--supplementary-dir expects LABEL=PATH")
        label, path = item.split("=", 1)
        supplementary_dirs.append((label, Path(path).resolve()))
    result = package(
        args.comparison_dir.resolve(),
        args.endpoint_dir.resolve(),
        args.output_dir.resolve(),
        args.archive.resolve() if args.archive else None,
        tuple(path.resolve() for path in args.supplementary_file),
        tuple(supplementary_dirs),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
