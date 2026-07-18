#!/usr/bin/env python3
"""Replay labeled AIOps Challenge 2020 fault windows into evidence objects.

The runner consumes a locally obtained daily ZIP and the official fault-label
CSV. It never republishes raw dataset rows. It compares each labeled window to
the preceding 30 minutes using robust median/MAD shifts and evaluates matched
negative windows one hour away. This is public-dataset replay evidence for the
MapEvidence/Normalize boundary, not an LLM reducer-quality experiment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

DATASET_URL = "https://github.com/NetManAIOps/AIOps-Challenge-2020-Data"
OUTER_ARCHIVE_MD5 = "fac7fe1b4e048c81ef88874334b73534"
METRIC_MEMBERS = {
    "docker": "2020_05_29/平台指标/dcos_docker.csv",
    "db": "2020_05_29/平台指标/db_oracle_11g.csv",
}


def _git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _timestamp_ms(raw: str) -> int:
    # The benchmark host timezone is Asia/Shanghai, matching the published
    # local timestamps and the epoch values in the daily metric files.
    parsed = datetime.strptime(raw.strip(), "%Y/%m/%d %H:%M")
    return int(parsed.timestamp() * 1000)


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


def _robust_shift(pre: list[float], window: list[float]) -> dict[str, float] | None:
    if len(pre) < 5 or len(window) < 2:
        return None
    pre_median = _median(pre)
    window_median = _median(window)
    mad = _median([abs(value - pre_median) for value in pre])
    # Dataset metrics are recorded at coarse integer/percentage resolution.
    # A one-unit floor prevents a constant-zero baseline from turning a small
    # absolute change into an unbounded robust score.
    scale = max(1.0, 1.4826 * mad, abs(pre_median) * 0.01)
    return {
        "pre_median": round(pre_median, 6),
        "window_median": round(window_median, 6),
        "robust_shift": round(abs(window_median - pre_median) / scale, 6),
    }


def _load_metric_index(daily_zip: Path) -> dict[str, dict[tuple[str, str], list[tuple[int, float]]]]:
    indexes: dict[str, dict[tuple[str, str], list[tuple[int, float]]]] = {}
    with zipfile.ZipFile(daily_zip) as archive:
        for kind, member in METRIC_MEMBERS.items():
            rows: dict[tuple[str, str], list[tuple[int, float]]] = {}
            with archive.open(member) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"))
                for row in reader:
                    try:
                        key = (str(row["cmdb_id"]), str(row["name"]))
                        rows.setdefault(key, []).append(
                            (int(row["timestamp"]), float(row["value"]))
                        )
                    except (KeyError, TypeError, ValueError):
                        continue
            indexes[kind] = rows
    return indexes


def _score_window(
    series: list[tuple[int, float]], start_ms: int, duration_ms: int
) -> dict[str, float] | None:
    pre = [value for stamp, value in series if start_ms - 30 * 60_000 <= stamp < start_ms]
    window = [value for stamp, value in series if start_ms <= stamp <= start_ms + duration_ms]
    return _robust_shift(pre, window)


def run_public_replay(
    *, daily_zip: Path, labels_csv: Path, threshold: float = 3.0
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    indexes = _load_metric_index(daily_zip)
    labels = list(csv.DictReader(labels_csv.open(encoding="utf-8-sig")))
    labels = [row for row in labels if str(row.get("start_time", "")).startswith("2020/5/29")]
    rows: list[dict[str, Any]] = []
    for label in labels:
        kind = str(label["object"]).strip()
        object_id = str(label["name"]).strip()
        kpis = [value.strip() for value in str(label.get("kpi", "")).split(";") if value.strip()]
        start_ms = _timestamp_ms(str(label["start_time"]))
        duration_ms = 5 * 60_000
        for window_class, offset_ms in (("fault", 0), ("negative-before", -60 * 60_000), ("negative-after", 60 * 60_000)):
            kpi_scores = []
            for kpi in kpis:
                score = _score_window(
                    indexes.get(kind, {}).get((object_id, kpi), []),
                    start_ms + offset_ms,
                    duration_ms,
                )
                if score is not None:
                    kpi_scores.append({"kpi": kpi, **score})
            max_shift = max((item["robust_shift"] for item in kpi_scores), default=0.0)
            predicted = max_shift >= threshold
            expected = window_class == "fault"
            evidence_id = hashlib.sha256(
                f"{label['index']}:{window_class}:{object_id}:{start_ms + offset_ms}".encode()
            ).hexdigest()[:16]
            rows.append(
                {
                    "label_index": int(label["index"]),
                    "window_class": window_class,
                    "object_type": kind,
                    "object_id": object_id,
                    "fault_type": str(label["fault_desrcibtion"]).strip(),
                    "start_ms": start_ms + offset_ms,
                    "expected_fault": expected,
                    "predicted_fault": predicted,
                    "max_robust_shift": round(max_shift, 6),
                    "evidence_id": evidence_id,
                    "source_ref": f"AIOps2020:2020_05_29:{object_id}:{start_ms + offset_ms}",
                    "kpi_scores": kpi_scores,
                }
            )
    tp = sum(row["expected_fault"] and row["predicted_fault"] for row in rows)
    fp = sum(not row["expected_fault"] and row["predicted_fault"] for row in rows)
    fn = sum(row["expected_fault"] and not row["predicted_fault"] for row in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    aggregate = {
        "label_count": len(labels),
        "window_count": len(rows),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "threshold": threshold,
    }
    return rows, aggregate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-zip", required=True)
    parser.add_argument("--labels-csv", required=True)
    parser.add_argument(
        "--threshold",
        type=float,
        default=3.0,
        help="Conventional robust-shift gate in median absolute deviations.",
    )
    parser.add_argument("--output-root", default=".sage/benchmarks/aiops2020_public_replay")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    daily_zip = Path(args.daily_zip).resolve()
    labels_csv = Path(args.labels_csv).resolve()
    rows, aggregate = run_public_replay(
        daily_zip=daily_zip, labels_csv=labels_csv, threshold=args.threshold
    )
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    label_digest = hashlib.sha256(labels_csv.read_bytes()).hexdigest()
    manifest = {
        "run_id": run_id,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_label": "replay",
        "dataset": "AIOps Challenge 2020",
        "source_url": DATASET_URL,
        "outer_archive_md5": OUTER_ARCHIVE_MD5,
        "daily_member": "AIOps挑战赛数据/2020_05_29.zip",
        "raw_data_archived": False,
        "label_sha256": label_digest,
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git": {"commit": _git_output(["rev-parse", "HEAD"]), "dirty": bool(_git_output(["status", "--porcelain"]))},
        "boundary": (
            "Public-dataset replay of MapEvidence/Normalize on four labeled May 29 "
            "faults plus matched negative windows; not semantic grouping or online LLM evidence."
        ),
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (outdir / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (outdir / "aggregate.json").write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (outdir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        flat = [{key: value for key, value in row.items() if key != "kpi_scores"} for row in rows]
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader(); writer.writerows(flat)
    print(f"RESULT_DIR={outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
