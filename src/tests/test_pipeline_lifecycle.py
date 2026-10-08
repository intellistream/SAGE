from __future__ import annotations

import threading

import pytest

from sage.foundation import MapFunction, SinkFunction, SourceFunction
from sage.runtime import BaseService, LocalEnvironment, PipelineCompiler
from sage.runtime.local_backend import LocalRuntimeAdapter


class ClosingSink(SinkFunction):
    def __init__(self, output, closed):
        super().__init__()
        self.output = output
        self.closed = closed

    def execute(self, value):
        self.output.append(value)

    def close(self):
        self.closed.append(self)


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("values", [[], [1, 2]])
def test_all_sink_replicas_close_once_including_empty_input(streaming, values):
    output, closed = [], []
    env = LocalEnvironment("sink-finalization")
    env.from_batch(values).sink(ClosingSink, output, closed, parallelism=2)
    job_id = env.submit(autostop=not streaming)
    try:
        record = env.jobmanager.jobs[job_id]
        if record.handle is not None:
            for thread in record.handle._threads:
                thread.join(timeout=3)
            assert not record.handle.is_running
        assert env.jobmanager.get_job_status(job_id)["status"] == "stopped"
        env.stop()
        assert output == values
        assert len(closed) == 2
        assert len({id(sink) for sink in closed}) == 2
    finally:
        env.jobmanager.delete_job(job_id, force=True)


def test_stream_failure_is_visible_and_closes_its_own_sinks():
    class Fail(MapFunction):
        def execute(self, value):
            raise ValueError("operator failed")

    output, closed = [], []
    env = LocalEnvironment("failing-stream")
    env.from_batch([1]).map(Fail).sink(ClosingSink, output, closed)
    job_id = env.submit(autostop=False)
    record = env.jobmanager.jobs[job_id]
    try:
        for thread in record.handle._threads:
            thread.join(timeout=3)
        status = env.jobmanager.get_job_status(job_id)
        assert status["status"] == "failed"
        assert status["success"] is False
        assert "operator failed" in status["error"]
        assert len(closed) == 1
        assert output == []
    finally:
        env.jobmanager.delete_job(job_id, force=True)


def test_stream_cleanup_does_not_wait_for_unrelated_jobs():
    entered, release = threading.Event(), threading.Event()

    class BlockingSource(SourceFunction):
        def execute(self):
            entered.set()
            release.wait(timeout=3)
            return None

    slow_closed, fast_closed = [], []
    slow = LocalEnvironment("slow-independent-job")
    slow.from_source(BlockingSource).sink(ClosingSink, [], slow_closed)
    slow_id = slow.submit(autostop=False)
    assert entered.wait(3)
    fast = LocalEnvironment("fast-independent-job")
    fast.from_batch([1]).sink(ClosingSink, [], fast_closed)
    fast_id = fast.submit(autostop=False)
    try:
        for thread in fast.jobmanager.jobs[fast_id].handle._threads:
            thread.join(timeout=3)
        assert len(fast_closed) == 1
        assert slow_closed == []
    finally:
        release.set()
        slow.stop()
        fast.jobmanager.delete_job(fast_id, force=True)
        slow.jobmanager.delete_job(slow_id, force=True)
    assert len(slow_closed) == 1


def test_batch_failure_closes_sink_replicas():
    class Fail(MapFunction):
        def execute(self, value):
            raise ValueError("batch failed")

    backend = LocalRuntimeAdapter()
    backend.start()
    closed = []
    env = LocalEnvironment("failing-batch")
    env.from_batch([1]).map(Fail).sink(ClosingSink, [], closed, parallelism=2)
    graph = PipelineCompiler().compile(env.pipeline, backend)
    try:
        with pytest.raises(ValueError, match="batch failed"):
            graph.submit(autostop=True)
        assert len(closed) == 2
    finally:
        backend.stop()


def test_linear_batch_service_context_is_available_and_closed():
    stopped = []

    class EchoService(BaseService):
        def process(self, value):
            return value * 10

        def stop(self):
            stopped.append(True)

    class ServiceMap(MapFunction):
        def execute(self, value):
            return self.call_service("echo", value)

    output, closed = [], []
    env = LocalEnvironment("batch-service")
    env.register_service("echo", EchoService)
    env.from_batch([1, 2]).map(ServiceMap).sink(ClosingSink, output, closed)
    job_id = env.submit(autostop=True)
    try:
        assert output == [10, 20]
        assert stopped == [True]
        assert len(closed) == 1
    finally:
        env.jobmanager.delete_job(job_id)


def test_batch_failure_drains_other_calls_before_cleanup():
    active, release, finished = threading.Event(), threading.Event(), threading.Event()
    closed = []

    class FailingAndSlow(MapFunction):
        def execute(self, value):
            if value == 0:
                assert active.wait(3)
                raise ValueError("first call failed")
            active.set()
            assert release.wait(3)
            finished.set()
            return value

    class CheckClose(SinkFunction):
        def execute(self, value):
            pass

        def close(self):
            assert finished.is_set()
            closed.append(True)

    backend = LocalRuntimeAdapter()
    backend.start()
    env = LocalEnvironment("drain-before-close")
    env.from_batch([0, 1]).map(FailingAndSlow, parallelism=2).sink(CheckClose)
    graph = PipelineCompiler().compile(env.pipeline, backend)
    failures = []

    def run():
        try:
            graph.submit(autostop=True)
        except ValueError as exc:
            failures.append(str(exc))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    try:
        assert active.wait(3)
        release.set()
        thread.join(timeout=3)
        assert not thread.is_alive()
        assert failures == ["first call failed"]
        assert closed == [True]
    finally:
        release.set()
        thread.join(timeout=3)
        backend.stop()


def test_partial_stream_construction_failure_still_closes_created_sinks():
    class FailToConstruct(SinkFunction):
        def __init__(self):
            raise ValueError("construction failed")

        def execute(self, value):
            pass

    env = LocalEnvironment("partial-construction")
    closed = []
    source = env.from_batch([1])
    source.sink(ClosingSink, [], closed)
    source.sink(FailToConstruct)
    backend = LocalRuntimeAdapter()
    backend.start()
    graph = PipelineCompiler().compile(env.pipeline, backend, autostop=False)
    try:
        with pytest.raises(ValueError, match="construction failed"):
            graph.submit(autostop=False)
        assert len(closed) == 1
    finally:
        backend.stop()
