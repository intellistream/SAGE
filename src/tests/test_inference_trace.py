from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.tracing import (
    NDJSONExporter,
    TraceConfig,
    Tracer,
    current_span,
    get_tracer,
    submit_traced,
    traced,
    use_tracer,
)
from sage.tracing.schema import normalize_record
from sage.tracing.view import read_events, timeline


class MemoryExporter:
    def __init__(self):
        self.records = []

    def export(self, record):
        self.records.append(json.loads(record))


@pytest.fixture
def capture():
    exporter = MemoryExporter()
    tracer = Tracer(exporter)
    with use_tracer(tracer):
        yield tracer, exporter
    assert tracer.close()


def test_default_noop_preserves_values_exceptions_and_creates_no_worker():
    before = set(threading.enumerate())
    assert not get_tracer().enabled
    marker = object()

    @traced("sage.test.step")
    def function():
        return marker

    assert function() is marker
    with pytest.raises(ValueError):
        with get_tracer().span("ignored"):
            raise ValueError("original")
    assert set(threading.enumerate()) == before


def test_nested_ids_threads_queue_and_concurrent_roots(capture):
    tracer, exporter = capture

    @traced("sage.test.operation")
    def operation():
        return current_span().trace_id

    with ThreadPoolExecutor(max_workers=4) as pool:
        with tracer.span("sage.test.pipeline", kind="pipeline") as root:
            futures = [submit_traced(pool, operation) for _ in range(4)]
            assert {f.result() for f in futures} == {root.trace_id}
        assert tracer.flush()
    for event in exporter.records:
        normalize_record(event)
    view = timeline(exporter.records)
    assert view["traces"][0]["state"] == "finished_observed"
    assert len({e["trace_id"] for e in exporter.records}) == 1
    assert any(s["links"] for s in view["traces"][0]["spans"])
    assert all(s["duration_ns"] >= 0 for s in view["traces"][0]["spans"])


def test_privacy_never_serializes_content_headers_reasoning_or_exception(capture):
    tracer, exporter = capture
    secret = "sk-canary-secret"

    class Dangerous:
        def __repr__(self):
            raise AssertionError("must never repr user data")

    with pytest.raises(RuntimeError):
        with tracer.span(
            "sage.model.call", kind="model", attributes={"authorization": secret, "model": secret}
        ) as span:
            span.summarize({"prompt": secret, "reasoning": secret, "obj": Dangerous()})
            span.summarize(secret)
            span.endpoint("https://user:password@host/api?token=" + secret)
            span.summary("PRIVATE " + secret)
            span.annotate(input_tokens=12, output_tokens=4, headers=secret)
            raise RuntimeError("sensitive-exception-" + secret)
    assert tracer.flush()
    encoded = json.dumps(exporter.records)
    assert secret not in encoded
    assert "sensitive-exception" not in encoded
    assert "https://" not in encoded
    assert "decision_summary" not in encoded
    end = next(e for e in exporter.records if e["event_type"] == "span_end")
    assert end["status"] == "error"
    assert end["attributes"]["input_tokens"] == 12
    assert end["attributes"]["error_type"] == "RuntimeError"
    assert any(ref.startswith("input-prefix-hmac-") for ref in end["evidence_refs"])


def test_sampling_applies_to_entire_trace_and_redactor_requires_optin():
    exporter = MemoryExporter()
    tracer = Tracer(exporter, TraceConfig(sample_rate=0))
    with use_tracer(tracer), tracer.span("root"):
        with tracer.span("child"):
            pass
    tracer.close()
    assert exporter.records == []
    with pytest.raises(ValueError):
        TraceConfig(allow_summaries=True)
    tracer = Tracer(
        exporter,
        TraceConfig(
            allow_summaries=True,
            summary_redactor=lambda _: "Public decision: used available evidence.",
        ),
    )
    with use_tracer(tracer), tracer.span("root") as span:
        span.summary("do-not-export-original")
    tracer.close()
    assert "do-not-export-original" not in json.dumps(exporter.records)
    assert any("decision_summary" in e for e in exporter.records)


def test_exporter_failure_and_queue_overflow_never_change_work():
    entered, release = threading.Event(), threading.Event()

    class Stalled:
        def export(self, record):
            entered.set()
            release.wait(3)
            raise OSError("private filesystem path")

    tracer = Tracer(Stalled(), TraceConfig(queue_capacity=2))
    try:
        with use_tracer(tracer), tracer.span("root"):
            assert entered.wait(3)
            for _ in range(50):
                with tracer.span("step"):
                    pass
        assert tracer.stats()["queue_depth"] <= 2
        assert tracer.stats()["dropped_events"] > 0
        assert not tracer.close(timeout=0.001)
    finally:
        release.set()
        assert tracer.close(timeout=3)
    assert tracer.stats()["export_errors"] > 0


def test_spool_rotation_retention_permissions_and_partial_read(tmp_path):
    exporter = NDJSONExporter(
        tmp_path, segment_bytes=16384, total_bytes=32768, retention_seconds=10
    )
    tracer = Tracer(exporter)
    with use_tracer(tracer):
        for _ in range(100):
            with tracer.span("root"):
                pass
    assert tracer.close(timeout=3)
    files = sorted(tmp_path.glob("trace-*.ndjson"))
    assert sum(p.stat().st_size for p in files) <= 32768
    assert all(p.stat().st_size <= 16384 for p in files)
    assert all(p.stat().st_mode & 0o077 == 0 for p in files)
    events = read_events(tmp_path)
    assert events
    with files[-1].open("ab") as stream:
        stream.write(b'{"partial":')
    assert read_events(tmp_path) == events
    for path in files:
        os.utime(path, (time.time() - 20, time.time() - 20))
    unrelated = tmp_path / "keep.txt"
    unrelated.write_text("keep")
    exporter.purge()
    assert not list(tmp_path.glob("trace-*.ndjson"))
    assert unrelated.exists()


def test_async_cancel_error_type_and_retry_link(capture):
    tracer, exporter = capture

    @traced("sage.tool.async", kind="tool")
    async def cancelled():
        raise asyncio.CancelledError("private")

    with tracer.span("pipeline", kind="pipeline"):
        with tracer.span("attempt", attributes={"attempt": 1}) as first:
            pass
        with tracer.span("attempt", links=[first.span_id], attributes={"attempt": 2}):
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(cancelled())
    assert tracer.flush()
    assert any(e.get("status") == "cancelled" for e in exporter.records)
    assert "private" not in json.dumps(exporter.records)
    path = timeline(exporter.records)["traces"][0]["critical_path"]
    assert path["dependency_completeness"] == "partial"


def test_wall_clock_jump_does_not_change_elapsed(capture, monkeypatch):
    tracer, exporter = capture
    with tracer.span("root"):
        monkeypatch.setattr("sage.tracing.core.time.time_ns", lambda: 1)
    assert tracer.flush()
    span = timeline(exporter.records)["traces"][0]["spans"][0]
    assert span["duration_ns"] >= 0


def test_reader_rejects_future_schema_unknown_fields_and_bounds(tmp_path, capture):
    tracer, exporter = capture
    with tracer.span("root"):
        pass
    assert tracer.flush()
    record = exporter.records[0]
    path = tmp_path / "input.ndjson"
    path.write_text(json.dumps({**record, "prompt": "must-not-display"}) + "\n")
    with pytest.raises(ValueError):
        read_events(path)
    path.write_text(json.dumps({**record, "schema_version": 99}) + "\n")
    with pytest.raises(ValueError):
        read_events(path)
    path.write_bytes(b"x" * 20000)
    with pytest.raises(ValueError):
        read_events(path)


def test_independent_executor_roots_and_cross_clock_dependencies(capture):
    tracer, exporter = capture
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [submit_traced(pool, lambda: current_span().trace_id) for _ in range(2)]
        assert len({future.result() for future in futures}) == 2
    assert tracer.flush()
    assert len(timeline(exporter.records)["traces"]) == 2
    records = []
    with tracer.span("root"):
        with tracer.span("first") as first:
            pass
        with tracer.span("second", links=[first.span_id]) as second:
            pass
    assert tracer.flush()
    for event in exporter.records:
        if event["trace_id"] == first.trace_id:
            changed = dict(event)
            if event["span_id"] == second.span_id:
                changed["clock_id"] = "other-clock"
            records.append(changed)
    path = timeline(records)["traces"][0]["critical_path"]
    assert "uncalibrated_clock_domains" in path["limitations"]
    assert path["dependency_completeness"] == "partial"


def test_producer_fixture_matches_reader_and_cli_contract():
    from pathlib import Path

    events = read_events(Path(__file__).parent / "fixtures" / "inference_trace_v1.ndjson")
    view = timeline(events)["traces"][0]
    assert view["state"] == "finished_observed"
    assert len(view["critical_path"]["span_ids"]) == 3


def test_opaque_values_and_bad_metadata_cannot_break_inference(capture):
    tracer, exporter = capture

    class Explosive:
        def __repr__(self):
            raise RuntimeError("private")

    with tracer.span("root") as span:
        span.summarize({"reasoning": "private", "items": [1, 2], "object": Explosive()})
        span.annotate(model="https://private-host", operation="/private/path")
    with tracer.span("bad-metadata", attributes=Explosive()):
        result = 42
    assert result == 42
    assert tracer.flush()
    assert "private" not in json.dumps(exporter.records)
    assert tracer.stats()["instrumentation_errors"] == 1


def test_cli_stable_snapshot_is_private_and_preserves_trace(tmp_path):
    from pathlib import Path

    from sage.cli.main import main

    source = Path(__file__).parent / "fixtures" / "inference_trace_v1.ndjson"
    output = tmp_path / "snapshot.ndjson"
    assert main(["trace", "export", "--source", str(source), "--output", str(output)]) == 0
    assert read_events(output) == read_events(source)
    assert output.stat().st_mode & 0o077 == 0
    assert main(["trace", "export", "--source", str(source), "--output", str(source)]) == 2
