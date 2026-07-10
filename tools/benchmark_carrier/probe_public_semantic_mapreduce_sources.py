#!/usr/bin/env python3
"""Probe public data candidates for Semantic MapReduce replay experiments.

The probe is intentionally conservative: it records availability, metadata,
and small sample artifacts, but it does not download multi-GB archives unless a
caller explicitly raises the size limit. The output is a benchmark artifact so
paper claims can distinguish "public source exists" from "full replay was run".
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = ".sage/benchmarks/public_semantic_mapreduce_sources"


SOURCES: tuple[dict[str, Any], ...] = (
    {
        "name": "aiops-challenge-2020",
        "kind": "labeled-dataset",
        "repo": "NetManAIOps/AIOps-Challenge-2020-Data",
        "signals": ["business metrics", "platform metrics", "traces", "fault table"],
    },
    {
        "name": "lo2",
        "kind": "labeled-dataset",
        "zenodo_record": "14938118",
        "signals": ["logs", "metrics", "limited traces", "anomaly labels"],
    },
    {
        "name": "opentelemetry-demo",
        "kind": "benchmark-substrate",
        "repo": "open-telemetry/opentelemetry-demo",
        "signals": ["metrics", "logs", "traces", "service graph"],
    },
    {
        "name": "deathstarbench",
        "kind": "benchmark-substrate",
        "repo": "delimitrou/DeathStarBench",
        "signals": ["microservice topology", "benchmark workloads"],
    },
    {
        "name": "illinois-firm-traces",
        "kind": "trace-dataset",
        "page": "https://databank.illinois.edu/datasets/IDB-6738796",
        "signals": ["preprocessed traces", "anomaly locations"],
    },
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe public data candidates for Semantic MapReduce."
    )
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--max-download-mb",
        type=float,
        default=64.0,
        help="Maximum per-file download size for optional samples.",
    )
    return parser.parse_args()


def _urlopen_json(url: str, *, timeout: int = 30) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "sage-semantic-mapreduce-probe",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _urlopen_text(url: str, *, timeout: int = 30) -> tuple[int, str, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "sage-semantic-mapreduce-probe"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, response.headers.get("content-type", ""), body


def _download(url: str, destination: Path, *, max_bytes: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "sage-semantic-mapreduce-probe"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        size = response.headers.get("content-length")
        content_length = int(size) if size and size.isdigit() else None
        if content_length is not None and content_length > max_bytes:
            return {
                "downloaded": False,
                "reason": "larger_than_max_download",
                "content_length": content_length,
                "max_bytes": max_bytes,
            }
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            return {
                "downloaded": False,
                "reason": "stream_exceeded_max_download",
                "content_length": content_length,
                "max_bytes": max_bytes,
            }
        destination.write_bytes(data)
        return {
            "downloaded": True,
            "path": str(destination),
            "bytes": len(data),
            "content_length": content_length,
        }


def _probe_github_repo(source: dict[str, Any], outdir: Path) -> dict[str, Any]:
    repo = source["repo"]
    result: dict[str, Any] = {
        "name": source["name"],
        "kind": source["kind"],
        "signals": source["signals"],
        "source_url": f"https://github.com/{repo}",
        "accessible": False,
        "files": [],
        "fit": "unknown",
    }
    try:
        contents = _urlopen_json(f"https://api.github.com/repos/{repo}/contents")
        result["accessible"] = True
        result["files"] = [
            {
                "name": item.get("name"),
                "path": item.get("path"),
                "type": item.get("type"),
                "size": item.get("size"),
            }
            for item in contents
        ]
        readme = next(
            (item for item in contents if str(item.get("name", "")).lower() == "readme.md"),
            None,
        )
        if readme and readme.get("download_url"):
            status, content_type, body = _urlopen_text(str(readme["download_url"]))
            readme_path = outdir / f"{source['name']}_README.md"
            readme_path.write_text(body, encoding="utf-8")
            result["readme"] = {
                "status": status,
                "content_type": content_type,
                "path": str(readme_path),
                "bytes": len(body.encode("utf-8")),
            }
        names = {str(item.get("name", "")) for item in contents}
        if source["name"] == "aiops-challenge-2020":
            result["fit"] = "requires_external_archive_download"
            result["notes"] = (
                "GitHub root exposes README and external cloud links; actual "
                "fault CSV and metric/trace zips are not downloadable from the "
                "GitHub API root."
            )
        elif source["name"] == "opentelemetry-demo":
            result["fit"] = "generator_or_live_replay_substrate"
            result["topology_hint"] = {
                "has_compose_yaml": "compose.yaml" in names,
                "has_otel_config": "otel-config.yml" in names,
            }
        elif source["name"] == "deathstarbench":
            result["fit"] = "benchmark_substrate_requires_deployment"
            result["topology_hint"] = {
                "service_dirs": sorted(
                    name
                    for name in names
                    if name
                    in {"socialNetwork", "hotelReservation", "mediaMicroservices"}
                )
            }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        result["error"] = repr(exc)
        result["fit"] = "probe_failed"
    return result


def _probe_zenodo(source: dict[str, Any], outdir: Path, *, max_bytes: int) -> dict[str, Any]:
    record = source["zenodo_record"]
    result: dict[str, Any] = {
        "name": source["name"],
        "kind": source["kind"],
        "signals": source["signals"],
        "source_url": f"https://zenodo.org/records/{record}",
        "accessible": False,
        "files": [],
        "fit": "unknown",
    }
    try:
        payload = _urlopen_json(f"https://zenodo.org/api/records/{record}")
        result["accessible"] = True
        result["doi"] = payload.get("doi")
        for file_info in payload.get("files", []):
            file_entry = {
                "key": file_info.get("key"),
                "size": file_info.get("size"),
                "download_url": file_info.get("links", {}).get("self"),
            }
            result["files"].append(file_entry)
            key = str(file_entry["key"])
            url = file_entry.get("download_url")
            if not url:
                continue
            if key in {"README.md", "lo2-scripts.zip", "data-appendix.pdf"}:
                sample = _download(
                    str(url),
                    outdir / f"{source['name']}_{key.replace('/', '_')}",
                    max_bytes=max_bytes,
                )
                if key.endswith(".zip") and sample.get("downloaded"):
                    with zipfile.ZipFile(sample["path"]) as archive:
                        sample["zip_members"] = archive.namelist()[:50]
                file_entry["sample_probe"] = sample
            elif key in {"lo2-sample.zip", "lo2-data.zip"}:
                file_entry["sample_probe"] = {
                    "downloaded": False,
                    "reason": "dataset_archive_not_downloaded_by_default",
                    "max_bytes": max_bytes,
                }
        result["fit"] = "sample_available_but_large_archive"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        result["error"] = repr(exc)
        result["fit"] = "probe_failed"
    return result


def _probe_page(source: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": source["name"],
        "kind": source["kind"],
        "signals": source["signals"],
        "source_url": source["page"],
        "accessible": False,
        "fit": "unknown",
    }
    try:
        status, content_type, body = _urlopen_text(source["page"])
        result["accessible"] = True
        result["http_status"] = status
        result["content_type"] = content_type
        result["bytes_sampled"] = len(body.encode("utf-8"))
        result["fit"] = "page_accessible_manual_download_needed"
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["error"] = str(exc)
        result["fit"] = "blocked_or_manual_access_required"
    except (urllib.error.URLError, TimeoutError) as exc:
        result["error"] = repr(exc)
        result["fit"] = "probe_failed"
    return result


def _git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _submodule_info(path: str) -> dict[str, Any]:
    module_path = Path(path)
    if not module_path.exists():
        return {"path": path, "present": False}

    def run(args: list[str]) -> str:
        try:
            return subprocess.check_output(
                ["git", "-C", path, *args], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    return {
        "path": path,
        "present": True,
        "commit": run(["rev-parse", "HEAD"]),
        "branch": run(["rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(run(["status", "--porcelain"])),
    }


def _write_manifest(outdir: Path, args: argparse.Namespace) -> None:
    manifest = {
        "run_id": outdir.name,
        "created_unix": int(time.time()),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command_args": vars(args),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git": {
            "commit": _git_output(["rev-parse", "HEAD"]),
            "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
            "dirty": bool(_git_output(["status", "--porcelain"])),
        },
        "evidence_label": "derived-artifact",
        "workload_source": {
            "kind": "public-source-probe",
            "path": "tools/benchmark_carrier/probe_public_semantic_mapreduce_sources.py",
            "suite": "public_semantic_mapreduce_sources",
        },
        "shared_workload_submodule": _submodule_info(
            "third_party/llm-serving-workloads"
        ),
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    _write_manifest(outdir, args)
    max_bytes = int(args.max_download_mb * 1024 * 1024)

    results: list[dict[str, Any]] = []
    for source in SOURCES:
        if "repo" in source:
            result = _probe_github_repo(source, outdir)
        elif "zenodo_record" in source:
            result = _probe_zenodo(source, outdir, max_bytes=max_bytes)
        else:
            result = _probe_page(source)
        results.append(result)
        print(
            f"source={result['name']} accessible={result['accessible']} "
            f"fit={result['fit']}"
        )

    (outdir / "source_probe.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (outdir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "kind",
                "accessible",
                "fit",
                "file_count",
                "source_url",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "name": result["name"],
                    "kind": result["kind"],
                    "accessible": result["accessible"],
                    "fit": result["fit"],
                    "file_count": len(result.get("files", [])),
                    "source_url": result["source_url"],
                }
            )
    print(f"RESULT_DIR={outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
