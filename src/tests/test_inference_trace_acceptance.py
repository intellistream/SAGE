from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path

import pytest
from inference_trace_workload import CANARIES, generate

from sage.tracing import NDJSONExporter, TraceConfig, Tracer, traced, use_tracer
from sage.tracing.schema import normalize_record
from sage.tracing.view import read_events, timeline


def test_real_workflow_semantics_and_failure_artifacts(tmp_path):
    manifest = generate(tmp_path)
    assert manifest["overflow"]["dropped_events"] > 0
    assert manifest["unavailable"]["export_errors"] > 0
    records = read_events(manifest["fixture"])
    cancelled = timeline(records, manifest["cancel_trace_id"])["traces"][0]
    assert cancelled["state"] == "finished_observed"
    assert any(s["status"] == "cancelled" for s in cancelled["spans"])


def test_adversarial_metadata_summary_bounds_and_async_input(tmp_path):
    tracer = Tracer(
        NDJSONExporter(tmp_path),
        TraceConfig(
            allow_summaries=True,
            summary_redactor=lambda value: "公开结论" * 100000,
        ),
    )

    @traced("acceptance.async", input_index=0)
    async def operation(value):
        return CANARIES[4]

    with (
        use_tracer(tracer),
        tracer.span(
            "acceptance.root",
            attributes={
                "Authorization": CANARIES[0],
                "model": CANARIES[2],
                "prompt": CANARIES[3],
                "output": CANARIES[4],
                "reasoning": CANARIES[6],
            },
        ) as span,
    ):
        span.summarize({"Authorization": CANARIES[0], "nested": [CANARIES[3], CANARIES[4]]})
        span.summary(CANARIES[3] * 100000)
        span.endpoint("invalid-utf8-\ud800")
        span.evidence("<script>" + CANARIES[0])
        span.evidence("x" * 100000)
        assert asyncio.run(operation(CANARIES[3])) == CANARIES[4]
    assert tracer.close(5)
    assert tracer.stats()["instrumentation_errors"] == 1
    raw = b"".join(p.read_bytes() for p in tmp_path.glob("*.ndjson"))
    assert all(c.encode() not in raw for c in CANARIES)
    default = read_events(tmp_path)
    assert all("decision_summary" not in e for e in default)
    explicit = read_events(tmp_path, include_summaries=True)
    summaries = [e["decision_summary"] for e in explicit if "decision_summary" in e]
    assert summaries and all(len(s.encode()) <= 256 for s in summaries)
    end = next(
        e for e in explicit if e.get("name") == "acceptance.async" and e["event_type"] == "span_end"
    )
    assert end["attributes"]["input_bytes"] == len(CANARIES[3])
    assert any(ref.startswith("input-prefix-hmac-") for ref in end["evidence_refs"])


def test_reader_rejects_lifecycle_collision_and_unobserved_root(tmp_path):
    tracer = Tracer(NDJSONExporter(tmp_path / "spool"))
    with use_tracer(tracer), tracer.span("root"):
        with tracer.span("child"):
            pass
    assert tracer.close(5)
    records = read_events(tmp_path / "spool")
    first = records[0]
    collision = {**first, "event_id": "distinct-event"}
    path = tmp_path / "collision.ndjson"
    path.write_text("".join(json.dumps(e) + "\n" for e in [*records, collision]))
    with pytest.raises(ValueError, match="lifecycle"):
        read_events(path)
    without_root = [
        e for e in records if e["span_id"] != first["span_id"] or e["event_type"] == "trace_end"
    ]
    assert timeline(without_root)["traces"][0]["state"] == "live_or_incomplete"
    for changes in [
        {"parent_span_id": "0" * 16},
        {"links": ["0" * 16]},
        {"kind": "bogus"},
        {"status": "running"},
    ]:
        with pytest.raises(ValueError):
            normalize_record({**first, **changes})


def test_metadata_processing_does_not_iterate_unbounded_inputs(tmp_path):
    tracer = Tracer(NDJSONExporter(tmp_path))

    def unbounded():
        raise AssertionError("do not evaluate lazy metadata")
        yield

    with use_tracer(tracer):
        with tracer.span("safe", links=unbounded()):
            value = 42
        with tracer.span("bounded", attributes={str(i): "x" for i in range(10000)}) as span:
            assert not span.attributes
    assert value == 42 and tracer.close(5)
    assert tracer.stats()["instrumentation_errors"] == 1


def test_shared_spool_budget_lock_and_concurrent_reader_purge(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    first = NDJSONExporter(tmp_path, segment_bytes=16384, total_bytes=16384)
    second = NDJSONExporter(tmp_path, segment_bytes=16384, total_bytes=16384)
    purge = first._purge

    def paused(reserve=0):
        purge(reserve)
        entered.set()
        assert release.wait(3)

    monkeypatch.setattr(first, "_purge", paused)
    writer = threading.Thread(target=first.export, args=(b"x" * 9000 + b"\n",))
    writer.start()
    assert entered.wait(3)
    tracer = Tracer(second)
    try:
        with use_tracer(tracer), tracer.span("contention"):
            result = 42
        assert tracer.flush(3)
        assert result == 42 and tracer.stats()["export_errors"] > 0
    finally:
        release.set()
        writer.join(3)
        tracer.close(3)
    second.export(b"y" * 9000 + b"\n")
    assert sum(p.stat().st_size for p in tmp_path.glob("*.ndjson")) <= 16384
    opening = Path.open

    def purged(path, *args, **kwargs):
        if path.name.startswith("trace-"):
            path.unlink(missing_ok=True)
        return opening(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", purged)
    assert read_events(tmp_path) == []


def test_terminal_status_freezes_and_close_cannot_strand_accepted_events(tmp_path, monkeypatch):
    tracer = Tracer(NDJSONExporter(tmp_path / "terminal"))
    emit = tracer._emit

    def late_error(span, event_type, **kwargs):
        emit(span, event_type, **kwargs)
        if event_type == "span_end":
            thread = threading.Thread(target=span.record_error, args=(ValueError("private"),))
            thread.start()
            thread.join(3)

    monkeypatch.setattr(tracer, "_emit", late_error)
    with use_tracer(tracer), tracer.span("terminal"):
        pass
    assert tracer.close(3)
    records = read_events(tmp_path / "terminal")
    assert {e["status"] for e in records if "status" in e} == {"ok"}

    tracer = Tracer(NDJSONExporter(tmp_path / "close"))
    entered, release = threading.Event(), threading.Event()
    put = tracer._queue.put_nowait

    def paused(record):
        entered.set()
        assert release.wait(3)
        return put(record)

    monkeypatch.setattr(tracer._queue, "put_nowait", paused)
    spans = []
    producer = threading.Thread(target=lambda: spans.append(tracer.start_span("close-race")))
    producer.start()
    assert entered.wait(3)
    closer = threading.Thread(target=tracer.close, kwargs={"timeout": 3})
    closer.start()
    time.sleep(0.08)  # Allow the old worker to exit between closed-check and enqueue.
    release.set()
    producer.join(3)
    closer.join(3)
    spans[0].end()
    stats = tracer.stats()
    assert stats["accepted_events"] == stats["exported_events"] == 1
    assert stats["dropped_events"] == 3  # root end, metrics and receipt after close
    assert stats["queue_depth"] == 0
