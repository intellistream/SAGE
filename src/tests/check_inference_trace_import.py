"""Validate a real SAGE artifact with the actual TraceLoom native importer.

PYTHONPATH=src python src/tests/check_inference_trace_import.py --fixture FILE --output DIR --traceloom BINARY
Perturbations are explicitly derived protocol fault probes, not new workflow runs.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from inference_trace_workload import CANARIES


def verify_follow(events, output, binary):
    directory = output / "live-spool"
    directory.mkdir()
    source = directory / "trace-live.ndjson"
    snapshot, database = output / "live-snapshot.ndjson", output / "live.db"
    html = output / "live.html"

    def publish(records):
        temporary = directory / "pending"
        temporary.write_text("".join(json.dumps(e) + "\n" for e in records))
        os.replace(temporary, source)

    def wait_for(predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if predicate():
                    return
            except (OSError, sqlite3.OperationalError):
                pass
            time.sleep(0.05)
        raise AssertionError("live snapshot did not refresh")

    def count():
        if not database.exists():
            return 0
        with sqlite3.connect(database) as connection:
            return connection.execute("select count(*) from traceloom_inference_event").fetchone()[
                0
            ]

    publish(events[: len(events) // 2])
    commands = [
        [
            sys.executable,
            "-m",
            "sage.cli.main",
            "trace",
            "export",
            "--source",
            str(directory),
            "--output",
            str(snapshot),
            "--follow",
        ],
        [
            str(binary),
            "import-inference",
            str(snapshot),
            "--output",
            str(database),
            "--html-out",
            str(html),
            "--follow",
        ],
    ]
    processes = []
    with (output / "live.log").open("w") as log:
        try:
            processes.append(subprocess.Popen(commands[0], stdout=log, stderr=log))
            wait_for(snapshot.exists)
            processes.append(subprocess.Popen(commands[1], stdout=log, stderr=log))
            wait_for(lambda: count() == len(events) // 2)
            publish(events)
            wait_for(lambda: count() == len(events))
            wait_for(lambda: html.exists() and 'http-equiv="refresh"' in html.read_text())
            assert all(c not in html.read_text() for c in CANARIES)
            assert all(process.poll() is None for process in processes)
        finally:
            for process in processes:
                process.send_signal(signal.SIGINT)
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return {
        "commands": commands,
        "first_events": len(events) // 2,
        "final_events": len(events),
        "html_refresh": True,
    }


def verify(fixture, output, binary):
    fixture, output = Path(fixture), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    events = [json.loads(line) for line in fixture.read_text().splitlines()]
    results = {
        "fixture": str(fixture.resolve()),
        "sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "binary": str(Path(binary).resolve()),
        "binary_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
        "runs": {},
    }

    def run(name, records, *, repeat=False, rejected=False, tail=b""):
        source, db = output / f"{name}.ndjson", output / f"{name}.db"
        if not repeat:
            assert not db.exists(), "use a fresh output directory"
            source.write_bytes(b"".join((json.dumps(e) + "\n").encode() for e in records) + tail)
        command = [
            str(binary),
            "import-inference",
            str(source),
            "--output",
            str(db),
            "--html-out",
            str(output / f"{name}.html"),
            "--perfetto-out",
            str(output / f"{name}.perfetto.json"),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        results["runs"][name + ("_repeat" if repeat else "")] = {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        assert (result.returncode != 0) == rejected, result.stderr
        if rejected:
            return None
        for path in [output / f"{name}.html", output / f"{name}.perfetto.json", db]:
            raw = path.read_bytes()
            assert all(c.encode() not in raw for c in CANARIES)
        connection = sqlite3.connect(db)
        assert connection.execute("select version from traceloom_inference_meta").fetchone()[0] == 1
        return connection

    db = run("original", events)
    assert db.execute("select count(*) from traceloom_inference_event").fetchone()[0] == len(events)
    statuses = {
        row[0] for row in db.execute("select terminal_status from traceloom_v_inference_span")
    }
    assert {"ok", "error", "cancelled"} <= statuses
    original_spans = db.execute(
        "select trace_id,span_id,duration_ns from traceloom_v_inference_span order by trace_id,span_id"
    ).fetchall()
    target = next(
        e
        for e in events
        if e["event_type"] == "span_start" and e.get("attributes", {}).get("attempt") == 2
    )
    # Exact two-attempt duration sum is observed; ancestry never enters this edge.
    ids = (target["span_id"], target["links"][0])
    durations = dict(
        db.execute(
            "select span_id,duration_ns from traceloom_v_inference_span where span_id in (?,?)", ids
        )
    )
    observed = db.execute(
        "select observed_path_ns,evidence_state from traceloom_inference_span_metric where span_id=?",
        (ids[0],),
    ).fetchone()
    assert observed == (sum(durations.values()), "partial_observed_dependencies")
    db.close()
    repeated = run("original", events, repeat=True)
    assert repeated.execute("select count(*) from traceloom_inference_event").fetchone()[0] == len(
        events
    )
    repeated.close()
    assert f"duplicates={len(events)}" in results["runs"]["original_repeat"]["stderr"]

    db = run("reversed", list(reversed(events)))
    assert (
        db.execute(
            "select trace_id,span_id,duration_ns from traceloom_v_inference_span order by trace_id,span_id"
        ).fetchall()
        == original_spans
    )
    db.close()
    partial = [
        e for e in events if not (e["span_id"] == ids[0] and e["event_type"] == "span_start")
    ]
    db = run("incomplete", partial, tail=b'{"schema_version":1')
    assert (
        db.execute(
            "select status from traceloom_v_inference_span where span_id=?", (ids[0],)
        ).fetchone()[0]
        == "missing_start"
    )
    assert (
        db.execute(
            "select state from traceloom_v_inference_trace where trace_id=?", (target["trace_id"],)
        ).fetchone()[0]
        == "finished_with_incomplete_spans"
    )
    db.close()
    clocks = copy.deepcopy(events)
    for event in clocks:
        if event["span_id"] == ids[0]:
            event["clock_id"] = "fault-probe-clock"
    db = run("cross-clock", clocks)
    assert (
        db.execute(
            "select timing_state from traceloom_v_inference_dependency where target_span_id=?",
            (ids[0],),
        ).fetchone()[0]
        == "cross_clock"
    )
    assert (
        db.execute(
            "select observed_path_ns from traceloom_inference_span_metric where span_id=?",
            (ids[0],),
        ).fetchone()[0]
        is None
    )
    db.close()
    future = copy.deepcopy(events[:1])
    future[0]["schema_version"] = 2
    run("future-version", future, rejected=True)
    results["follow"] = verify_follow(events, output, binary)
    results["checks"] = [
        "v1",
        "idempotent",
        "reversed",
        "incomplete",
        "partial-tail",
        "retry-path-exact",
        "cross-clock-no-sum",
        "future-version-rejected",
        "privacy-files-html-perfetto",
        "sage-atomic-snapshot-to-traceloom-live-refresh",
    ]
    (output / "report.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--traceloom", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.fixture, args.output, args.traceloom), indent=2))
