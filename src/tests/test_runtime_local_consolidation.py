from __future__ import annotations

import time

from sage.foundation import BatchFunction, MapFunction, SinkFunction
from sage.runtime import LocalEnvironment
from sage.runtime.exception_hooks import (
    get_registered_exception_handler_hook,
    register_kernel_exception_handler_hook,
)
from sage.runtime.job_manager import JobManager
from sage.runtime.scheduler import FIFOScheduler, LoadAwareScheduler, resolve_scheduler
from sage.stream._runtime_kernel_types import Packet, StopSignal


class NumberBatchSource(BatchFunction):
    def __init__(self) -> None:
        super().__init__()
        self._current = 0

    def execute(self):
        if self._current >= 4:
            return StopSignal("numbers-done")
        value = self._current
        self._current += 1
        return value


class DoubleValue(MapFunction):
    def execute(self, data: int) -> int:
        return data * 2


class CollectSink(SinkFunction):
    collected: list[int] = []

    def execute(self, data: int) -> None:
        type(self).collected.append(data)


class SlowTickSource(BatchFunction):
    def __init__(self) -> None:
        super().__init__()
        self._current = 0

    def execute(self):
        time.sleep(0.02)
        self._current += 1
        return self._current


def test_packet_and_stop_signal_are_main_repo_owned() -> None:
    signal = StopSignal("done", source="source-1")
    packet = Packet(payload={"x": 1}, input_index=2, partition_key="k", partition_strategy="hash")

    copied = packet.copy()
    rekeyed = packet.update_key("k2")

    assert signal.name == "done"
    assert signal.source == "source-1"
    assert copied == packet
    assert rekeyed.partition_key == "k2"
    assert packet.inherit_partition_info("payload").partition_strategy == "hash"


def test_scheduler_resolution_uses_in_tree_implementations() -> None:
    fifo = resolve_scheduler(scheduler="fifo", platform="local")
    load_aware = resolve_scheduler(scheduler="load_aware", platform="local")

    assert isinstance(fifo, FIFOScheduler)
    assert isinstance(load_aware, LoadAwareScheduler)
    assert fifo.get_metrics()["scheduler_type"] == "FIFO"
    assert load_aware.get_metrics()["scheduler_type"] == "LoadAware"


def test_local_environment_batch_submit_runs_without_kernel_dependency() -> None:
    CollectSink.collected = []
    JobManager().cleanup_all_jobs()

    env = LocalEnvironment(name="batch-test")
    env.from_batch(NumberBatchSource).map(DoubleValue).sink(CollectSink)

    env_uuid = env.submit(autostop=True)
    status = env.jobmanager.get_job_status(env_uuid)

    assert CollectSink.collected == [0, 2, 4, 6]
    assert status["status"] == "stopped"
    assert status["pipeline_size"] == 3


def test_local_environment_streaming_job_can_be_stopped() -> None:
    JobManager().cleanup_all_jobs()

    env = LocalEnvironment(name="stream-test")
    env.from_batch(SlowTickSource).map(DoubleValue).sink(CollectSink)

    env_uuid = env.submit(autostop=False)
    status = env.jobmanager.get_job_status(env_uuid)
    assert status["status"] == "running"

    env.stop()
    stopped_status = env.jobmanager.get_job_status(env_uuid)
    assert stopped_status["status"] == "stopped"


def test_exception_hook_registration_is_owned_in_tree() -> None:
    pushed: list[str] = []

    def push(handler):
        pushed.append("push")

    def pop():
        pushed.append("pop")

    register_kernel_exception_handler_hook(push, pop)
    registered_push, registered_pop = get_registered_exception_handler_hook()

    assert registered_push is push
    assert registered_pop is pop
