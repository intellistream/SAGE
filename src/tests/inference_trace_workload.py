"""CPU-only acceptance workload. Run with PYTHONPATH=src python this_file --output DIR.

Events come from actual LocalEnvironment execution and chat's HTTP call path. Only
the HTTP transport is fake; no model service, network, credentials or NPU is used.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import logging
import os
import threading
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sage.cli.commands.apps import chat
from sage.foundation import MapFunction, SinkFunction, SourceFunction
from sage.runtime import LocalEnvironment, StopSignal
from sage.tracing import NDJSONExporter, TraceConfig, Tracer, get_tracer, use_tracer
from sage.tracing.view import read_events, timeline

CANARIES = (
    "sk-acceptance-token-canary",
    "Authorization",
    "https://private.invalid/v1?token=url-canary",
    "raw-prompt-canary",
    "raw-output-canary",
    "exception-body-canary",
    "hidden-reasoning-canary",
)


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return json.dumps(
            {
                "choices": [{"message": {"content": CANARIES[4], "reasoning": CANARIES[6]}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }
        ).encode()


class ModelStep(MapFunction):
    def execute(self, mode):
        previous = None
        for attempt in range(1, 3 if mode == "retry" else 2):
            with get_tracer().span(
                "acceptance.attempt",
                attributes={"attempt": attempt},
                links=[previous.span_id] if previous and previous.enabled else [],
            ) as span:
                status = chat._request_openai_chat(
                    CANARIES[3],
                    SimpleNamespace(
                        model="deterministic-fake",
                        engine="sagellm",
                        stream=False,
                        base_url=CANARIES[2],
                        api_key_env="SAGE_TRACE_ACCEPTANCE_KEY",
                        timeout=1,
                    ),
                )
                if status:
                    span.record_error(RuntimeError(CANARIES[5]))
                else:
                    return status
            previous = span
        raise ValueError(CANARIES[5])


class Collect(SinkFunction):
    values = []

    def execute(self, value):
        self.values.append(value)


def run_batch(mode, tracer=None):
    Collect.values = []
    calls = 0

    def transport(*args, **kwargs):
        nonlocal calls
        calls += 1
        if mode == "error" or (mode == "retry" and calls == 1):
            raise urllib.error.URLError(CANARIES[5])
        return Response()

    env = LocalEnvironment("trace-acceptance")
    env.from_batch([mode]).keyby(lambda value: 0).map(ModelStep).sink(Collect)
    output, errors = io.StringIO(), io.StringIO()
    exception = None
    result = None
    old_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with (
            patch.object(chat.urllib.request, "urlopen", transport),
            patch.dict(os.environ, {"SAGE_TRACE_ACCEPTANCE_KEY": CANARIES[0]}),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
            use_tracer(tracer) if tracer else contextlib.nullcontext(),
        ):
            try:
                result = env.submit(autostop=True)
                assert result == env.env_uuid
                result = "submitted_job_id"
            except Exception as exc:
                exception = (type(exc).__name__, str(exc))
    finally:
        env.jobmanager.delete_job(env.env_uuid, force=True)
        logging.disable(old_logging)
    # Sensitive original results stay in memory only, for equality checks.
    return result, list(Collect.values), exception, output.getvalue(), errors.getvalue()


def run_cancel(tracer, directory):
    entered, release = threading.Event(), threading.Event()

    class Blocking(SourceFunction):
        def execute(self):
            entered.set()
            if not release.wait(5):
                raise TimeoutError("acceptance synchronization")
            return StopSignal("done")

    env = LocalEnvironment("trace-cancel")
    env.from_source(Blocking).sink(Collect)
    with use_tracer(tracer):
        job = env.submit(autostop=False)
    try:
        assert entered.wait(5) and tracer.flush(5)
        trace_id = env.jobmanager.get_job_status(job)["trace_id"]
        live = timeline(read_events(directory), trace_id)["traces"][0]
        assert live["state"] == "live_or_incomplete"
        handle = env.jobmanager.jobs[job].handle
        handle.stop(timeout=0)
        release.set()
        handle.stop(timeout=5)
        assert not handle.is_running
        return trace_id
    finally:
        release.set()
        env.jobmanager.delete_job(job, force=True)


class GateExporter:
    def __init__(self, delegate):
        self.delegate = delegate
        self.entered, self.release = threading.Event(), threading.Event()

    def export(self, record):
        self.entered.set()
        if not self.release.wait(5):
            raise TimeoutError("acceptance synchronization")
        self.delegate.export(record)


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    spool = output / "spool"
    assert not spool.exists(), "use a fresh output directory"
    tracer = Tracer(NDJSONExporter(spool))
    results = {}
    for mode in ["success", "retry", "error"]:
        disabled = run_batch(mode)
        enabled = run_batch(mode, tracer)
        assert disabled == enabled
        results[mode] = {
            "semantics_equal": True,
            "exception_type": enabled[2][0] if enabled[2] else None,
        }
    results["cancel_trace_id"] = run_cancel(tracer, spool)
    assert tracer.close(5)

    gate = GateExporter(NDJSONExporter(spool))
    overflowing = Tracer(gate, TraceConfig(queue_capacity=1))
    with use_tracer(overflowing):
        blocker = overflowing.start_span("acceptance.exporter_blocker")
        assert gate.entered.wait(5)
        assert run_batch("success", overflowing) == run_batch("success")
        assert overflowing.stats()["dropped_events"] > 0
    gate.release.set()
    assert overflowing.flush(5)
    blocker.end()
    assert overflowing.flush(5)
    # Capacity 1 could itself lose a receipt; publish the measured counter explicitly.
    with use_tracer(overflowing):
        receipt = overflowing.start_span("acceptance.drop_receipt")
        assert overflowing.flush(5)
        overflowing._emit(
            receipt, "metrics", attributes={"dropped_events": overflowing.stats()["dropped_events"]}
        )
        assert overflowing.flush(5)
        receipt.end()
    assert overflowing.close(5)
    results["overflow"] = overflowing.stats()

    blocked_path = output / "unavailable"
    blocked_path.write_bytes(b"not a directory")
    unavailable = Tracer(NDJSONExporter(blocked_path))
    for mode in ["success", "error"]:
        assert run_batch(mode, unavailable) == run_batch(mode)
    assert unavailable.close(5)
    assert unavailable.stats()["export_errors"] > 0
    results["unavailable"] = unavailable.stats()

    events = read_events(spool)
    fixture = output / "workflow.ndjson"
    # Preserve producer records verbatim, not reader-normalized records.
    fixture.write_bytes(
        b"".join(path.read_bytes() for path in sorted(spool.glob("trace-*.ndjson")))
    )
    encoded = fixture.read_text()
    for canary in CANARIES:
        assert canary not in encoded
        assert canary not in json.dumps(timeline(events))
    names = {e.get("name") for e in events}
    assert {
        "sage.runtime.pipeline",
        "sage.runtime.operator",
        "sage.runtime.packet_queue",
        "sage.model.http",
    } <= names
    statuses = {e.get("status") for e in events}
    assert {"ok", "error", "cancelled"} <= statuses
    attempts = [e for e in events if e.get("attributes", {}).get("attempt") == 2]
    assert attempts and any(e.get("links") for e in attempts)
    results.update(
        {
            "fixture": str(fixture.resolve()),
            "sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "events": len(events),
            "trace_ids": sorted({e["trace_id"] for e in events}),
            "tracer": tracer.stats(),
        }
    )
    (output / "manifest.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    print(json.dumps(generate(parser.parse_args().output), indent=2))
