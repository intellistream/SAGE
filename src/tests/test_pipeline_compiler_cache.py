from __future__ import annotations

import gc
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.foundation import FlatMapFunction, MapFunction, SinkFunction
from sage.runtime import CompiledPlanCache, LocalEnvironment, PipelineCompiler
from sage.runtime.flownet_backend import FlowNetRuntimeAdapter
from sage.runtime.local_backend import LocalRuntimeAdapter


class Offset(MapFunction):
    def __init__(self, offset=0):
        super().__init__()
        self.offset = offset
        self.calls = 0

    def execute(self, data):
        self.calls += 1
        return data + self.offset


class Collect(SinkFunction):
    def __init__(self, output):
        super().__init__()
        self.output = output

    def execute(self, data):
        self.output.append(data)


@pytest.fixture(params=[LocalRuntimeAdapter, FlowNetRuntimeAdapter], ids=["local", "flownet"])
def adapter(request):
    backend = request.param()
    backend.start()
    yield backend
    backend.stop()


def pipeline(values, output, *, offset=0, parallelism=1, name="cache-test"):
    env = LocalEnvironment(name)
    env.from_batch(values).map(Offset, offset, parallelism=parallelism).sink(Collect, output)
    return env


def test_cache_reuses_structure_but_rebinds_inputs_functions_and_actors(adapter):
    cache = CompiledPlanCache()
    compiler = PipelineCompiler(cache)
    first_output, second_output = [], []
    first_env = pipeline([1, 2], first_output, offset=10)
    second_env = pipeline([3], second_output, offset=20, name="another-request")
    first = compiler.compile(first_env.pipeline, adapter)
    second = compiler.compile(second_env.pipeline, adapter)

    assert first.compiled_plan is second.compiled_plan
    assert first.actor_handles[0] is not second.actor_handles[0]
    first.submit(autostop=True)
    second.submit(autostop=True)
    assert first_output == [11, 12]
    assert second_output == [23]
    assert first._instances is not second._instances
    assert cache.stats().compiles == 1
    assert cache.stats().hits == 1
    with pytest.raises(RuntimeError, match="single-use"):
        first.submit(autostop=True)


def test_default_environment_submissions_share_only_the_static_plan():
    first_output, second_output = [], []
    first_env = pipeline([1], first_output)
    second_env = pipeline([8], second_output)
    first_id = first_env.submit(autostop=True)
    second_id = second_env.submit(autostop=True)
    first = first_env.jobmanager.jobs[first_id].compiled_graph
    second = second_env.jobmanager.jobs[second_id].compiled_graph
    try:
        assert first.compiled_plan is second.compiled_plan
        assert first is not second
        assert first_output == [1]
        assert second_output == [8]
    finally:
        first_env.jobmanager.delete_job(first_id)
        second_env.jobmanager.delete_job(second_id)


def test_cached_plan_does_not_retain_request_or_user_function(adapter):
    compiler = PipelineCompiler(CompiledPlanCache())

    class Request:
        pass

    def bind_request():
        request = Request()

        class RequestMap(MapFunction):
            def execute(self, data):
                return request

        env = LocalEnvironment("private-request-name")
        env.from_batch([request]).map(RequestMap).sink(Collect, [])
        graph = compiler.compile(env.pipeline, adapter, autostop=False)
        return weakref.ref(request), weakref.ref(RequestMap), weakref.ref(env), graph.compiled_plan

    request_ref, class_ref, env_ref, plan = bind_request()
    gc.collect()
    assert request_ref() is None
    assert class_ref() is None
    assert env_ref() is None
    assert "private-request-name" not in plan.fingerprint.contract_json
    assert compiler.plan_cache.stats().entries == 1


def test_function_replacement_is_bound_without_caching_executable_code(adapter):
    compiler = PipelineCompiler(CompiledPlanCache())
    output = []
    env = pipeline([1], output)
    first = compiler.compile(env.pipeline, adapter, autostop=False)
    env.pipeline[1].function_class = type(
        "Replacement", (MapFunction,), {"execute": lambda self, data: data * 100}
    )
    env.pipeline[1].function_args = ()
    second = compiler.compile(env.pipeline, adapter, autostop=False)
    assert first.compiled_plan is second.compiled_plan
    second.submit(autostop=True)
    assert output == [100]


@pytest.mark.parametrize("change", ["parallelism", "edges", "kind", "services"])
def test_execution_structure_changes_invalidate_the_plan(adapter, change):
    compiler = PipelineCompiler(CompiledPlanCache())
    env = pipeline([1], [])
    first = compiler.compile(env.pipeline, adapter, autostop=False)
    if change == "parallelism":
        env.pipeline[1].parallelism = 2
    elif change == "edges":
        source, mapper, sink = env.pipeline
        sink.upstreams = [source]
        source.downstreams[sink.basename] = 0
        mapper.downstreams.clear()
    elif change == "kind":
        env = LocalEnvironment("filter")
        env.from_batch([1]).filter(lambda value: value > 0).sink(Collect, [])
    else:
        env.service_factories["new-service"] = object()
    second = compiler.compile(env.pipeline, adapter, autostop=False)
    assert first.compiled_plan.fingerprint != second.compiled_plan.fingerprint
    assert compiler.plan_cache.stats().compiles == 2


def test_cache_ttl_lru_and_bypass_are_respected_at_pipeline_entry(adapter):
    now = [0.0]
    cache = CompiledPlanCache(max_entries=2, ttl_seconds=10, clock=lambda: now[0])
    compiler = PipelineCompiler(cache)

    def compile_at(parallelism):
        env = pipeline([1], [], parallelism=parallelism)
        return compiler.compile(env.pipeline, adapter, autostop=False).compiled_plan

    first = compile_at(1)
    compile_at(2)
    assert compile_at(1) is first  # Touch A, making B the LRU entry.
    compile_at(3)
    assert cache.stats().evictions == 1
    assert compile_at(1) is first
    compile_at(2)
    assert cache.stats().compiles == 4
    now[0] = 11.0
    assert compile_at(1) is not first
    before = cache.stats()
    uncached = PipelineCompiler(cache, use_cache=False)
    env = pipeline([1], [])
    a = uncached.compile(env.pipeline, adapter, autostop=False)
    b = uncached.compile(env.pipeline, adapter, autostop=False)
    assert a.compiled_plan is not b.compiled_plan
    assert cache.stats() == before


def test_concurrent_compile_coalesces_structure_and_keeps_bindings_independent(adapter):
    cache = CompiledPlanCache()
    entered, release = threading.Event(), threading.Event()

    class SlowCompiler(PipelineCompiler):
        @staticmethod
        def _compile_structure(structure):
            entered.set()
            assert release.wait(3)
            return PipelineCompiler._compile_structure(structure)

    compiler = SlowCompiler(cache)
    outputs = [[] for _ in range(8)]
    environments = [pipeline([i], outputs[i]) for i in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(compiler.compile, env.pipeline, adapter) for env in environments]
        try:
            assert entered.wait(3)
            deadline = time.monotonic() + 3
            while cache.stats().waits < 7 and time.monotonic() < deadline:
                time.sleep(0.001)
            assert cache.stats().waits == 7
        finally:
            release.set()
        graphs = [f.result(timeout=3) for f in futures]
    assert cache.stats().compiles == 1
    assert len({id(g.compiled_plan) for g in graphs}) == 1
    assert len({id(g.actor_handles[0]) for g in graphs}) == 8
    for graph in graphs:
        graph.submit(autostop=True)
    assert outputs == [[i] for i in range(8)]


def test_runtime_binding_failure_does_not_poison_plan_cache(adapter):
    compiler = PipelineCompiler(CompiledPlanCache())

    class FailingConstructor(MapFunction):
        def __init__(self, *args):
            raise ValueError("request-specific failure")

        def execute(self, data):
            return data

    env = pipeline([1], [])
    env.pipeline[1].function_class = FailingConstructor
    with pytest.raises(ValueError, match="request-specific failure"):
        compiler.compile(env.pipeline, adapter)
    output = []
    graph = compiler.compile(pipeline([2], output).pipeline, adapter)
    graph.submit(autostop=True)
    assert output == [2]
    assert compiler.plan_cache.stats().compiles == 1
    assert compiler.plan_cache.stats().compile_failures == 0


def test_branching_batch_uses_graph_edges_instead_of_pipeline_list_order(adapter):
    left, right = [], []
    env = LocalEnvironment("branches")
    source = env.from_batch([1, 2])
    source.map(lambda value: value + 10).sink(Collect, left)
    source.map(lambda value: value * 100).sink(Collect, right)
    graph = PipelineCompiler().compile(env.pipeline, adapter)
    assert graph.actor_handles == []
    graph.submit(autostop=True)
    assert left == [11, 12]
    assert right == [100, 200]


def test_linear_execution_follows_edges_when_pipeline_storage_is_reordered(adapter):
    output = []
    env = pipeline([1, 2], output, offset=10)
    source, mapper, sink = env.pipeline
    graph = PipelineCompiler().compile([sink, source, mapper], adapter)
    graph.submit(autostop=True)
    assert output == [11, 12]


def test_linear_batch_does_not_construct_duplicate_downstream_functions(adapter):
    constructed = []
    output = []

    class CountedMap(MapFunction):
        def __init__(self):
            super().__init__()
            constructed.append(self)

        def execute(self, data):
            return data

    env = LocalEnvironment("one-instance-per-replica")
    env.from_batch([1, 2]).map(CountedMap, parallelism=2).sink(Collect, output)
    PipelineCompiler().compile(env.pipeline, adapter).submit(autostop=True)
    assert len(constructed) == 2
    assert output == [1, 2]


@pytest.mark.parametrize("streaming", [False, True])
def test_flatmap_outputs_and_none_map_agree_across_execution_paths(adapter, streaming):
    class EmitAndReturn(FlatMapFunction):
        def execute(self, data):
            self.collect({"collected": data})
            return {"returned": data}

    output = []
    env = LocalEnvironment("output-semantics")
    env.from_batch([1, 2]).map(lambda value: value if value == 1 else None).flatmap(
        EmitAndReturn
    ).sink(Collect, output)
    graph = PipelineCompiler().compile(env.pipeline, adapter, autostop=not streaming)
    handle = graph.submit(autostop=not streaming)
    if handle is not None:
        for thread in handle._threads:
            thread.join(timeout=3)
        assert not handle.is_running
        assert handle.error is None
    assert output == [{"returned": 1}, {"collected": 1}]


@pytest.mark.parametrize("parallelism", [1, 2])
def test_stateful_replica_never_processes_overlapping_calls(adapter, parallelism):
    class StatefulMap(MapFunction):
        def __init__(self):
            super().__init__()
            self.active = False
            self.calls = 0

        def execute(self, data):
            assert not self.active, "same replica was entered concurrently"
            self.active = True
            try:
                time.sleep(0.01)
                self.calls += 1
                return self.ctx.parallel_index, self.calls
            finally:
                self.active = False

    output = []
    env = LocalEnvironment("stateful-replicas")
    env.from_batch(list(range(8))).map(StatefulMap, parallelism=parallelism).sink(Collect, output)
    PipelineCompiler().compile(env.pipeline, adapter).submit(autostop=True)
    for replica in range(parallelism):
        counts = sorted(count for index, count in output if index == replica)
        assert counts == list(range(1, 8 // parallelism + 1))
