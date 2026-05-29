from __future__ import annotations

import threading
import time

import pytest

from sage.foundation import MapFunction, SinkFunction
from sage.runtime import FlowNetEnvironment, LocalEnvironment
from sage.runtime.backend import get_runtime_backend
from sage.runtime.flownet_backend import FlowNetRuntimeAdapter
from sage.runtime.job_manager import JobManager
from sage.runtime.pipeline_compiler import PipelineCompiler


class CollectItems(SinkFunction):
    collected: list[int] = []

    def execute(self, data: int) -> None:
        type(self).collected.append(int(data))


class SlowParallelMap(MapFunction):
    active_calls = 0
    max_active_calls = 0
    _lock = threading.Lock()

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls.active_calls = 0
            cls.max_active_calls = 0

    def execute(self, data: int) -> int:
        with type(self)._lock:
            type(self).active_calls += 1
            type(self).max_active_calls = max(type(self).max_active_calls, type(self).active_calls)

        try:
            time.sleep(0.05)
            return int(data)
        finally:
            with type(self)._lock:
                type(self).active_calls -= 1


class RecordKeyedReplica(MapFunction):
    def execute(self, data: dict[str, int | str]) -> dict[str, int | str]:
        return {
            "key": str(data["key"]),
            "replica": int(getattr(self.ctx, "parallel_index", -1)),
        }


class CollectAssignments(SinkFunction):
    collected: list[dict[str, int | str]] = []

    def execute(self, data: dict[str, int | str]) -> None:
        type(self).collected.append(data)


class CloseTrackingSink(SinkFunction):
    collected: list[int] = []
    close_calls = 0

    @classmethod
    def reset(cls) -> None:
        cls.collected = []
        cls.close_calls = 0

    def execute(self, data: int) -> None:
        type(self).collected.append(int(data))

    def close(self) -> None:
        type(self).close_calls += 1


def test_pipeline_compiler_bridges_parallelism_to_flownet_actor_replicas() -> None:
    adapter = FlowNetRuntimeAdapter()
    adapter.start()
    try:
        env = FlowNetEnvironment(name="flownet-parallelism-compile")
        env.from_batch([0, 1]).map(SlowParallelMap, parallelism=2).sink(CollectItems)

        compiled = PipelineCompiler().compile(env.pipeline, adapter)

        map_handle = compiled.actor_handles[0]
        sink_handle = compiled.actor_handles[1]
        assert getattr(map_handle, "replica_count", 1) == 2
        assert getattr(sink_handle, "replica_count", 1) == 1
    finally:
        adapter.stop()


def test_flownet_linear_batch_submit_uses_actor_stage_path(monkeypatch: pytest.MonkeyPatch) -> None:
    CollectItems.collected = []
    SlowParallelMap.reset()

    backend = get_runtime_backend()
    backend.stop()
    backend.start()
    try:
        env = FlowNetEnvironment(name="flownet-linear-stage-path")
        env.from_batch([0, 1, 2, 3]).map(SlowParallelMap, parallelism=2).sink(CollectItems)

        compiled = PipelineCompiler().compile(env.pipeline, backend)

        def _fail_worker_runtime(*args, **kwargs):
            raise AssertionError(
                "FlowNet linear batch submit should not start local worker runtime"
            )

        monkeypatch.setattr(compiled, "_start_worker_runtime", _fail_worker_runtime)

        compiled.submit(autostop=True)

        assert sorted(CollectItems.collected) == [0, 1, 2, 3]
        assert SlowParallelMap.max_active_calls >= 2
    finally:
        backend.stop()


def test_flownet_stage_ops_batch_closes_only_actor_sink_once() -> None:
    CloseTrackingSink.reset()

    backend = get_runtime_backend()
    backend.stop()
    backend.start()
    try:
        env = FlowNetEnvironment(name="flownet-stage-ops-sink-close")
        env.from_batch([0, 1]).map(SlowParallelMap, parallelism=2).sink(CloseTrackingSink)

        compiled = PipelineCompiler().compile(env.pipeline, backend)
        compiled.submit(autostop=True)

        assert sorted(CloseTrackingSink.collected) == [0, 1]
        assert CloseTrackingSink.close_calls == 1
    finally:
        backend.stop()


@pytest.mark.parametrize(
    ("environment_cls", "label"),
    [
        (LocalEnvironment, "local"),
        (FlowNetEnvironment, "flownet"),
    ],
)
def test_parallel_map_executes_concurrently_across_runtime_environments(
    environment_cls: type[LocalEnvironment | FlowNetEnvironment],
    label: str,
) -> None:
    CollectItems.collected = []
    SlowParallelMap.reset()

    if environment_cls is LocalEnvironment:
        JobManager().cleanup_all_jobs()
    else:
        backend = get_runtime_backend()
        backend.stop()
        backend.start()

    env = environment_cls(name=f"parallel-contract-{label}")
    env.from_batch([0, 1, 2, 3]).map(SlowParallelMap, parallelism=2).sink(CollectItems)

    try:
        env.submit(autostop=True)
        assert sorted(CollectItems.collected) == [0, 1, 2, 3]
        assert SlowParallelMap.max_active_calls >= 2
    finally:
        if environment_cls is FlowNetEnvironment:
            get_runtime_backend().stop()


@pytest.mark.parametrize(
    ("environment_cls", "label"),
    [
        (LocalEnvironment, "local"),
        (FlowNetEnvironment, "flownet"),
    ],
)
def test_keyed_parallel_map_keeps_stable_replica_across_runtime_environments(
    environment_cls: type[LocalEnvironment | FlowNetEnvironment],
    label: str,
) -> None:
    CollectAssignments.collected = []

    if environment_cls is LocalEnvironment:
        JobManager().cleanup_all_jobs()
    else:
        backend = get_runtime_backend()
        backend.stop()
        backend.start()

    env = environment_cls(name=f"parallel-keyed-contract-{label}")
    (
        env.from_batch(
            [
                {"key": "alpha", "value": 1},
                {"key": "beta", "value": 2},
                {"key": "alpha", "value": 3},
                {"key": "beta", "value": 4},
            ]
        )
        .keyby(lambda item: item["key"])
        .map(RecordKeyedReplica, parallelism=2)
        .sink(CollectAssignments)
    )

    try:
        env.submit(autostop=True)

        replica_by_key: dict[str, int] = {}
        for assignment in CollectAssignments.collected:
            key = str(assignment["key"])
            replica = int(assignment["replica"])
            previous = replica_by_key.setdefault(key, replica)
            assert previous == replica

        assert set(replica_by_key) == {"alpha", "beta"}
    finally:
        if environment_cls is FlowNetEnvironment:
            get_runtime_backend().stop()
