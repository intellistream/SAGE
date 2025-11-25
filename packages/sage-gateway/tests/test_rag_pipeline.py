"""Unit tests for the gateway RAG pipeline service."""

from __future__ import annotations

import queue

import pytest
from sage.gateway import rag_pipeline
from sage.gateway.rag_pipeline import (
    PipelineBridge,
    RAGChatMap,
    RAGChatSink,
    RAGChatSource,
    RAGPipelineService,
)


class DummyPipelineBuilder:
    """Fluent helper that mimics the chaining interface used by LocalEnvironment."""

    def __init__(self, env: "DummyEnvironment"):
        self._env = env

    def map(self, map_cls, **kwargs):
        self._env.map_cls = map_cls
        self._env.map_kwargs = kwargs
        return self

    def sink(self, sink_cls, **kwargs):
        self._env.sink_cls = sink_cls
        self._env.sink_kwargs = kwargs
        return self


class DummyEnvironment:
    """Minimal stand-in for LocalEnvironment used in tests."""

    def __init__(self, *args, **kwargs):
        self.source_cls = None
        self.source_args = None
        self.source_kwargs = None
        self.map_cls = None
        self.sink_cls = None
        self.autostop = None
        self.submitted = False

    def from_source(self, source_cls, *args, **kwargs):
        self.source_cls = source_cls
        self.source_args = args
        self.source_kwargs = kwargs
        return DummyPipelineBuilder(self)

    def submit(self, autostop: bool = False):
        self.autostop = autostop
        self.submitted = True
        return "dummy-job-id"


class EagerBridge(PipelineBridge):
    def __init__(self, response_payload):
        super().__init__()
        self.response_payload = response_payload
        self.last_payload = None

    def submit(self, payload):
        self.last_payload = payload
        q = queue.Queue()
        q.put(self.response_payload)
        return q


class HangingBridge(PipelineBridge):
    def __init__(self):
        super().__init__()
        self.last_payload = None

    def submit(self, payload):  # pragma: no cover - simple override
        self.last_payload = payload
        return queue.Queue()


def test_pipeline_bridge_submit_and_next():
    bridge = PipelineBridge()
    response_q = bridge.submit({"messages": []})

    request = bridge.next(timeout=0.01)
    assert request is not None
    assert request["payload"] == {"messages": []}
    assert request["response_queue"] is response_q


def test_pipeline_bridge_close_blocks_submit():
    bridge = PipelineBridge()
    bridge.close()

    with pytest.raises(RuntimeError):
        bridge.submit({})

    assert bridge.next(timeout=0.01) is None


def test_rag_pipeline_service_start_initializes_components(monkeypatch):
    monkeypatch.setattr(rag_pipeline, "LocalEnvironment", DummyEnvironment)

    service = RAGPipelineService()
    service.start()

    assert service._started is True
    assert isinstance(service.env, DummyEnvironment)

    env: DummyEnvironment = service.env
    assert env.source_cls is RAGChatSource
    assert env.map_cls is RAGChatMap
    assert env.sink_cls is RAGChatSink
    assert env.autostop is False
    assert service.job == "dummy-job-id"


def test_rag_pipeline_service_process_returns_payload(monkeypatch):
    service = RAGPipelineService()
    service.bridge = EagerBridge({"content": "ok"})
    service._started = True

    result = service.process({"messages": []})

    assert result == {"content": "ok"}
    assert service.bridge.last_payload == {"messages": []}


def test_rag_pipeline_service_process_timeout(monkeypatch):
    service = RAGPipelineService()
    bridge = HangingBridge()
    service.bridge = bridge
    service._started = True

    result = service.process({"messages": []}, timeout=0.01)

    assert result["error"] == "Response timeout"
    assert "超时" in result["content"]


def test_rag_pipeline_service_process_requires_start():
    service = RAGPipelineService()

    with pytest.raises(RuntimeError):
        service.process({"messages": []})
