from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import pytest

from sage.cli.commands.apps import chat
from sage.cli.main import main
from sage.foundation import SinkFunction, SourceFunction
from sage.runtime import FlowNetEnvironment, LocalEnvironment, StopSignal
from sage.runtime.backend import get_runtime_backend
from sage.tracing import (
    NDJSONExporter,
    Tracer,
    get_tracer,
    inject_context,
    use_trace_context,
    use_tracer,
)
from sage.tracing.view import read_events, timeline


class Collect(SinkFunction):
    values = []

    def execute(self, data):
        self.values.append(data)


@pytest.mark.parametrize("environment", [LocalEnvironment, FlowNetEnvironment])
@pytest.mark.parametrize("keyed", [False, True])
def test_pipeline_parentage_and_unchanged_outputs(tmp_path, environment, keyed):
    Collect.values = []
    tracer = Tracer(NDJSONExporter(tmp_path))
    env = environment("trace-test")
    stream = env.from_batch([1, 2, 3])
    if keyed:
        stream = stream.keyby(lambda value: value % 2)
    stream.map(lambda value: value * 2, parallelism=2).sink(Collect)
    try:
        with use_tracer(tracer):
            env.submit(autostop=True)
        assert tracer.close()
        assert Collect.values == [2, 4, 6]
        events = read_events(tmp_path)
        snapshot = timeline(events)
        assert len(snapshot["traces"]) == 1
        view = snapshot["traces"][0]
        assert view["state"] == "finished_observed"
        root = next(s for s in view["spans"] if s["parent_span_id"] is None)
        assert root["name"] == "sage.runtime.pipeline"
        assert any(s["name"] == "sage.runtime.operator" for s in view["spans"])
        assert all(s["parent_span_id"] is not None for s in view["spans"] if s is not root)
    finally:
        tracer.close()
        if environment is FlowNetEnvironment:
            get_runtime_backend().stop()
        else:
            env.jobmanager.delete_job(env.env_uuid, force=True)


def test_streaming_receipt_waits_for_sources_and_cli_shows_live(tmp_path, capsys):
    entered, release = threading.Event(), threading.Event()

    class Blocking(SourceFunction):
        def execute(self):
            entered.set()
            assert release.wait(3)
            return StopSignal("done")

    tracer = Tracer(NDJSONExporter(tmp_path))
    env = LocalEnvironment("stream-trace")
    env.from_source(Blocking).sink(Collect)
    with use_tracer(tracer):
        job_id = env.submit(autostop=False)
    try:
        assert entered.wait(3)
        assert tracer.flush()
        assert main(["trace", "show", "--source", str(tmp_path), "--json"]) == 0
        assert json.loads(capsys.readouterr().out)["traces"][0]["state"] == "live_or_incomplete"
        assert env.jobmanager.get_job_status(job_id)["trace_id"]
        release.set()
        handle = env.jobmanager.jobs[job_id].handle
        for thread in handle._threads:
            thread.join(3)
        assert tracer.flush()
        assert timeline(read_events(tmp_path))["traces"][0]["state"] == "finished_observed"
    finally:
        release.set()
        env.jobmanager.delete_job(job_id, force=True)
        tracer.close()


def test_model_usage_and_secrets_not_exported(tmp_path, monkeypatch, capsys):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {"message": {"content": "private-answer", "reasoning": "never-export"}}
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 3},
                }
            ).encode()

    monkeypatch.setattr(chat.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    monkeypatch.setenv("TRACE_TEST_KEY", "sk-test-secret")
    args = SimpleNamespace(
        model="test-model",
        engine="sagellm",
        stream=False,
        base_url="https://host/v1?auth=private-url",
        api_key_env="TRACE_TEST_KEY",
        timeout=1,
    )
    tracer = Tracer(NDJSONExporter(tmp_path))
    with use_tracer(tracer):
        assert chat._request_openai_chat("private-prompt", args) == 0
    tracer.close()
    capsys.readouterr()
    events = read_events(tmp_path)
    encoded = json.dumps(events)
    for value in [
        "sk-test-secret",
        "private-prompt",
        "private-answer",
        "never-export",
        "private-url",
    ]:
        assert value not in encoded
    end = next(e for e in events if e["event_type"] == "span_end")
    assert end["attributes"]["model"] == "test-model"
    assert end["attributes"]["input_tokens"] == 10
    assert end["attributes"]["output_tokens"] == 3


def test_remote_carrier_and_tool_retrieval_extension_points(tmp_path):
    tracer = Tracer(NDJSONExporter(tmp_path))
    with use_tracer(tracer), tracer.span("sage.pipeline", kind="pipeline") as root:
        carrier = inject_context()
        with use_tracer(tracer), use_trace_context(carrier):
            with get_tracer().span("sage.retrieval.search", kind="retrieval") as retrieval:
                retrieval.annotate(retrieved_count=2)
                retrieval.evidence("document-opaque-123")
            with get_tracer().span(
                "sage.tool.lookup", kind="tool", links=[retrieval.span_id]
            ) as tool:
                tool.annotate(attempt=1)
    tracer.close()
    view = timeline(read_events(tmp_path))["traces"][0]
    assert len(view["spans"]) == 3
    assert all(
        s["parent_span_id"] == root.span_id for s in view["spans"] if s["span_id"] != root.span_id
    )
    assert view["critical_path"]["span_ids"] == [retrieval.span_id, tool.span_id]
    with pytest.raises(ValueError):
        with use_trace_context({**carrier, "authorization": "unsafe"}):
            pass


def test_streaming_model_usage_only_frame_is_observed(tmp_path, capsys):
    tracer = Tracer(NDJSONExporter(tmp_path))
    lines = [
        b'data: {"choices":[{"delta":{"content":"answer","reasoning":"private"}}]}\n',
        b'data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":2}}\n',
        b"data: [DONE]\n",
    ]
    with use_tracer(tracer), tracer.span("sage.model.sse", kind="model"):
        chat._stream_sse_response(lines)
    tracer.close()
    assert capsys.readouterr().out == "answer\n"
    end = next(e for e in read_events(tmp_path) if e["event_type"] == "span_end")
    assert end["attributes"]["output_tokens"] == 2
    assert "private" not in json.dumps(end)


def test_stream_failure_is_reported_in_trace_without_changing_runtime_contract(tmp_path):
    class Fail(SourceFunction):
        def execute(self):
            raise ValueError("private-failure-body")

    tracer = Tracer(NDJSONExporter(tmp_path))
    env = LocalEnvironment("failed-trace")
    env.from_source(Fail).sink(Collect)
    with use_tracer(tracer):
        job_id = env.submit(autostop=False)
    try:
        handle = env.jobmanager.jobs[job_id].handle
        for thread in handle._threads:
            thread.join(3)
        assert tracer.flush()
        records = read_events(tmp_path)
        receipt = next(e for e in records if e["event_type"] == "trace_end")
        assert receipt["status"] == "error"
        assert "private-failure-body" not in json.dumps(records)
    finally:
        tracer.close()
        env.jobmanager.delete_job(job_id, force=True)
