"""Main-repo owned lightweight pipeline compiler for runtime-backed execution."""

from __future__ import annotations

import concurrent.futures
import hashlib
import logging
import queue as queue_module
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from sage.foundation import Collector, CustomLogger, FlatMapFunction
from sage.stream._runtime_kernel_types import Packet

from .actor_wrappers import (
    FilterActorWrapper,
    FlatMapActorWrapper,
    MapActorWrapper,
    ServiceActorWrapper,
    SinkActorWrapper,
    SourceActorWrapper,
)

logger = logging.getLogger(__name__)

__all__ = ["PipelineCompiler", "CompiledActorGraph", "_StreamingFlowHandle"]

_OP_MAP = "map"
_OP_FLATMAP = "flatmap"
_OP_FILTER = "filter"
_OP_SINK = "sink"
_WORKER_STOP = object()


def _transformation_name(t: Any) -> str:
    return type(t).__name__


def _classify(t: Any) -> tuple[type, str, str]:
    name = _transformation_name(t)
    if name == "SourceTransformation":
        return (SourceActorWrapper, "source", "run")
    if name == "BatchTransformation":
        return (SourceActorWrapper, "source", "run")
    if name == "MapTransformation":
        return (MapActorWrapper, _OP_MAP, "process")
    if name == "FlatMapTransformation":
        return (FlatMapActorWrapper, _OP_FLATMAP, "process")
    if name == "FilterTransformation":
        return (FilterActorWrapper, _OP_FILTER, "accepts")
    if name == "SinkTransformation":
        return (SinkActorWrapper, _OP_SINK, "consume")
    return (ServiceActorWrapper, _OP_MAP, "process")


def _uses_legacy_linear_wrapper(t: Any) -> bool:
    return _transformation_name(t) in {
        "MapTransformation",
        "FlatMapTransformation",
        "FilterTransformation",
        "SinkTransformation",
    }


def _replica_count_for(transformation: Any) -> int:
    if _classify(transformation)[1] == "source":
        return 1
    return max(1, int(getattr(transformation, "parallelism", 1) or 1))


def _actor_config_for(transformation: Any) -> dict[str, Any] | None:
    replica_count = _replica_count_for(transformation)
    if replica_count <= 1:
        return None
    return {
        "parallelism": replica_count,
        "materialization_policy_override": {
            "replica_policy": {
                "mode": "fixed",
                "count": replica_count,
            }
        },
    }


def _stable_partition_index(key: Any, replica_count: int) -> int:
    if replica_count <= 1:
        return 0
    digest = hashlib.blake2b(repr(key).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False) % replica_count


class _LightweightServiceFuture:
    def __init__(
        self,
        future: concurrent.futures.Future,
        progress_callback: Any | None = None,
    ) -> None:
        self._future = future
        self._progress_callback = progress_callback

    def result(self, timeout: float | None = None) -> Any:
        if self._progress_callback is None:
            return self._future.result(timeout=timeout)

        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            if self._future.done():
                return self._future.result()

            progressed = bool(self._progress_callback())
            if self._future.done():
                return self._future.result()

            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("Local service call did not complete before timeout.")

            if not progressed:
                time.sleep(0.01)

    def cancel(self) -> bool:
        return self._future.cancel()

    @property
    def done(self) -> bool:
        return self._future.done()


class _LightweightExecutionContext:
    def __init__(
        self,
        name: str,
        service_runtime: _LightweightServiceRuntime | None,
        *,
        parallel_index: int = 0,
        parallelism: int = 1,
    ) -> None:
        self.name = name
        self._service_runtime = service_runtime
        self._logger = CustomLogger(name=name)
        self._current_key: Any = None
        self.parallel_index = parallel_index
        self.parallelism = parallelism

    @property
    def logger(self) -> CustomLogger:
        return self._logger

    def set_current_key(self, key: Any) -> None:
        self._current_key = key

    def clear_key(self) -> None:
        self._current_key = None

    def get_key(self) -> Any:
        return self._current_key

    def get_service(self, service_name: str) -> Any:
        if self._service_runtime is None:
            raise RuntimeError(f"Service '{service_name}' is not available in the lightweight context")
        return self._service_runtime.get_service(service_name)

    def call_service(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if self._service_runtime is None:
            raise RuntimeError(f"Service '{service_name}' is not available in the lightweight context")
        return self._service_runtime.call_service(
            service_name,
            *args,
            timeout=timeout,
            method=method,
            **kwargs,
        )

    def call_service_async(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> concurrent.futures.Future:
        if self._service_runtime is None:
            raise RuntimeError(f"Service '{service_name}' is not available in the lightweight context")
        return self._service_runtime.call_service_async(
            service_name,
            *args,
            timeout=timeout,
            method=method,
            **kwargs,
        )


class _LightweightServiceRuntime:
    def __init__(
        self,
        service_factories: dict[str, Any],
        *,
        progress_callback: Any | None = None,
    ) -> None:
        self._service_factories = dict(service_factories)
        self._services: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._progress_callback = progress_callback
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(4, len(service_factories) or 1),
            thread_name_prefix="sage_local_service",
        )

    def _create_service(self, service_name: str) -> Any:
        factory = self._service_factories.get(service_name)
        if factory is None:
            raise RuntimeError(f"Service '{service_name}' is not registered in this environment")

        service_ctx = _LightweightExecutionContext(service_name, self)
        service = factory.create_service(service_ctx)

        setup = getattr(service, "setup", None)
        if callable(setup):
            setup()

        start = getattr(service, "start", None)
        if callable(start):
            start()
        else:
            start_running = getattr(service, "start_running", None)
            if callable(start_running):
                start_running()

        return service

    def get_service(self, service_name: str) -> Any:
        with self._lock:
            if service_name not in self._services:
                self._services[service_name] = self._create_service(service_name)
            return self._services[service_name]

    def _invoke_service(
        self,
        service_name: str,
        *args: Any,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        service = self.get_service(service_name)
        candidate_methods = [method] if method else ["process", "execute", "call"]
        for method_name in candidate_methods:
            if method_name is None:
                continue
            target = getattr(service, method_name, None)
            if callable(target):
                return target(*args, **kwargs)
        raise AttributeError(
            f"Service '{service_name}' does not expose a callable method for {candidate_methods}."
        )

    def call_service(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        return self.call_service_async(
            service_name,
            *args,
            timeout=timeout,
            method=method,
            **kwargs,
        ).result(timeout=timeout)

    def call_service_async(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> _LightweightServiceFuture:
        future = self._executor.submit(
            self._invoke_service,
            service_name,
            *args,
            method=method,
            **kwargs,
        )
        return _LightweightServiceFuture(future, self._progress_callback)

    def close(self) -> None:
        with self._lock:
            services = list(self._services.values())
            self._services.clear()

        for service in services:
            stop = getattr(service, "stop", None)
            if callable(stop):
                stop()
            else:
                terminate = getattr(service, "terminate", None)
                if callable(terminate):
                    terminate()

            cleanup = getattr(service, "cleanup", None)
            if callable(cleanup):
                cleanup()

        self._executor.shutdown(wait=True)


def _is_stop_signal(item: Any) -> bool:
    return item is None or type(item).__name__ == "StopSignal"


def _is_batch_source(transformation: Any) -> bool:
    return _transformation_name(transformation) == "BatchTransformation"


def _is_stream_source(transformation: Any) -> bool:
    return _transformation_name(transformation) == "SourceTransformation"


class _StreamingFlowHandle:
    def __init__(
        self,
        source_threads: list[threading.Thread] | threading.Thread | None,
        *,
        worker_threads: list[threading.Thread] | None = None,
        stop_event: threading.Event,
        shutdown_callback: Any | None = None,
    ) -> None:
        if source_threads is None:
            self._source_threads: list[threading.Thread] = []
        elif isinstance(source_threads, list):
            self._source_threads = source_threads
        else:
            self._source_threads = [source_threads]
        self._worker_threads = list(worker_threads or [])
        self._stop_event = stop_event
        self._shutdown_callback = shutdown_callback

    def stop(self, timeout: float = 30.0) -> None:
        self._stop_event.set()
        deadline = time.monotonic() + timeout
        for thread in self._source_threads:
            if not thread.is_alive():
                continue
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(timeout=remaining)

        if callable(self._shutdown_callback):
            self._shutdown_callback()

        for thread in self._worker_threads:
            if not thread.is_alive():
                continue
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(timeout=remaining)

    @property
    def is_running(self) -> bool:
        return any(thread.is_alive() for thread in [*self._source_threads, *self._worker_threads])


@dataclass
class CompiledActorGraph:
    stage_ops: list[tuple[str, Any]]
    source_transformation: Any | None
    actor_handles: list[Any] = field(default_factory=list)
    adapter: Any = None
    source_transformations: list[Any] = field(default_factory=list)
    pipeline: list[Any] = field(default_factory=list)
    downstream_edges: dict[str, list[tuple[Any, int]]] = field(default_factory=dict)
    _instances: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _dispatch_lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _service_runtime: _LightweightServiceRuntime | None = field(default=None, init=False, repr=False)
    _finalized: bool = field(default=False, init=False, repr=False)
    _closed_sources: set[str] = field(default_factory=set, init=False, repr=False)
    _replica_round_robin: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _source_poll_locks: dict[str, threading.Lock] = field(default_factory=dict, init=False, repr=False)
    _worker_queues: dict[str, list[queue_module.Queue[Any]]] = field(
        default_factory=dict, init=False, repr=False
    )
    _worker_threads: list[threading.Thread] = field(default_factory=list, init=False, repr=False)
    _worker_shutdown_started: bool = field(default=False, init=False, repr=False)
    _worker_shutdown_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )
    _worker_failure: BaseException | None = field(default=None, init=False, repr=False)
    _active_stream_sources: int = field(default=0, init=False, repr=False)

    def _platform(self) -> str | None:
        if not self.pipeline:
            return None
        env = getattr(self.pipeline[0], "env", None)
        return getattr(env, "platform", None)

    def _can_submit_via_stage_ops(self) -> bool:
        if self._platform() != "flownet":
            return False
        if len(self.source_transformations) != 1:
            return False
        if not self.stage_ops:
            return False

        if len(self.downstream_edges.get(self.source_transformations[0].basename, [])) > 1:
            return False

        proc_transformations = [
            transformation for transformation in self.pipeline if _classify(transformation)[1] != "source"
        ]
        if len(proc_transformations) != len(self.stage_ops):
            return False

        for transformation in proc_transformations:
            if len(getattr(transformation, "upstreams", [])) > 1:
                return False
            if len(self.downstream_edges.get(transformation.basename, [])) > 1:
                return False
        return True

    def _get_service_runtime(self) -> _LightweightServiceRuntime | None:
        if self._service_runtime is not None:
            return self._service_runtime
        if not self.pipeline:
            return None
        env = getattr(self.pipeline[0], "env", None)
        service_factories = getattr(env, "service_factories", {})
        if not service_factories:
            return None
        self._service_runtime = _LightweightServiceRuntime(
            service_factories,
            progress_callback=self._cooperative_service_pump,
        )
        return self._service_runtime

    def _cooperative_service_pump(self) -> bool:
        if not self._instances:
            return False
        return self._pump_stream_sources_once(self._instances)

    def _build_instances(self) -> dict[str, Any]:
        if self._instances:
            return self._instances

        instances: dict[str, Any] = {}
        service_runtime = self._get_service_runtime()
        for transformation in self.pipeline:
            replica_count = _replica_count_for(transformation)
            replica_group: list[Any] = []
            for replica_index in range(replica_count):
                function = transformation.function_class(
                    *transformation.function_args,
                    **transformation.function_kwargs,
                )
                context_name = transformation.basename
                if replica_count > 1:
                    context_name = f"{transformation.basename}_r{replica_index}"
                function.ctx = _LightweightExecutionContext(
                    context_name,
                    service_runtime,
                    parallel_index=replica_index,
                    parallelism=replica_count,
                )
                replica_group.append(function)
            instances[transformation.basename] = replica_group
        self._instances = instances
        return instances

    def _replicas_for(self, transformation: Any, instances: dict[str, Any]) -> list[Any]:
        replica_group = instances[transformation.basename]
        if isinstance(replica_group, list):
            return replica_group
        return [replica_group]

    def _source_poll_lock_for(self, transformation: Any) -> threading.Lock:
        with self._dispatch_lock:
            return self._source_poll_locks.setdefault(transformation.basename, threading.Lock())

    def _select_replica_index(self, transformation: Any, packet: Packet | None, replica_count: int) -> int:
        if replica_count <= 1:
            return 0
        if packet is not None and packet.is_keyed():
            return _stable_partition_index(packet.partition_key, replica_count)

        with self._dispatch_lock:
            current = int(self._replica_round_robin.get(transformation.basename, 0))
            selected = current % replica_count
            self._replica_round_robin[transformation.basename] = current + 1
        return selected

    def _select_function(
        self,
        transformation: Any,
        packet: Packet | None,
        instances: dict[str, Any],
        replica_index: int | None = None,
    ) -> Any:
        replicas = self._replicas_for(transformation, instances)
        if replica_index is not None:
            return replicas[replica_index]
        return replicas[self._select_replica_index(transformation, packet, len(replicas))]

    def _downstreams_for(self, transformation: Any) -> list[tuple[Any, int]]:
        return self.downstream_edges.get(transformation.basename, [])

    def _start_worker_runtime(
        self,
        instances: dict[str, Any],
        stop_event: threading.Event,
    ) -> None:
        if self._worker_queues:
            return

        for transformation in self.pipeline:
            if _classify(transformation)[1] == "source":
                continue

            replica_queues: list[queue_module.Queue[Any]] = []
            for replica_index, _ in enumerate(self._replicas_for(transformation, instances)):
                work_queue: queue_module.Queue[Any] = queue_module.Queue()
                worker = threading.Thread(
                    target=self._run_replica_worker,
                    args=(transformation, replica_index, work_queue, instances, stop_event),
                    daemon=True,
                    name=f"sage-worker-{transformation.basename}-r{replica_index}",
                )
                worker.start()
                self._worker_threads.append(worker)
                replica_queues.append(work_queue)

            self._worker_queues[transformation.basename] = replica_queues

    def _enqueue_for_processing(
        self,
        transformation: Any,
        packet: Packet,
        instances: dict[str, Any],
    ) -> None:
        replica_queues = self._worker_queues.get(transformation.basename)
        if not replica_queues:
            raise RuntimeError(
                f"Worker runtime is not initialized for transformation '{transformation.basename}'."
            )

        replica_index = self._select_replica_index(transformation, packet, len(replica_queues))
        replica_queues[replica_index].put(packet)

    def _enqueue_downstreams(
        self,
        transformation: Any,
        packet: Packet,
        instances: dict[str, Any],
    ) -> None:
        for downstream, input_index in self._downstreams_for(transformation):
            forwarded = packet.copy()
            forwarded.input_index = input_index
            self._enqueue_for_processing(downstream, forwarded, instances)

    def _normalize_outputs(self, result: Any, collector: Collector | None = None) -> list[Any]:
        outputs: list[Any] = []
        if result is not None:
            if hasattr(result, "__iter__") and not isinstance(result, (str, bytes, dict)):
                outputs.extend(list(result))
            else:
                outputs.append(result)
        if collector is not None:
            outputs.extend(collector.get_collected_data())
        return outputs

    def _cleanup_actor_handles(self) -> None:
        for handle in self.actor_handles:
            cancel = getattr(handle, "cancel", None)
            if callable(cancel):
                cancel()

    def _process_packet(
        self,
        transformation: Any,
        packet: Packet,
        instances: dict[str, Any],
        replica_index: int | None = None,
    ) -> None:
        function = self._select_function(
            transformation,
            packet,
            instances,
            replica_index=replica_index,
        )
        transformation_name = type(transformation).__name__
        function_ctx = getattr(function, "ctx", None)

        if packet.payload is None:
            return

        if function_ctx is not None and hasattr(function_ctx, "set_current_key"):
            function_ctx.set_current_key(packet.partition_key)

        try:
            if transformation_name == "KeyByTransformation":
                key = function.execute(packet.payload)
                self._enqueue_downstreams(
                    transformation,
                    packet.update_key(key, getattr(transformation, "partition_strategy", None)),
                    instances,
                )
                return

            if transformation_name == "FilterTransformation":
                if function.execute(packet.payload):
                    self._enqueue_downstreams(transformation, packet, instances)
                return

            if transformation_name == "FlatMapTransformation":
                collector = Collector(logger=getattr(function, "logger", None))
                if isinstance(function, FlatMapFunction):
                    function.insert_collector(collector)
                result = function.execute(packet.payload)
                for item in self._normalize_outputs(result, collector):
                    self._enqueue_downstreams(transformation, packet.inherit_partition_info(item), instances)
                return

            if transformation_name == "JoinTransformation":
                if not packet.is_keyed():
                    logger.warning(
                        "JoinTransformation '%s' received non-keyed packet; dropping payload.",
                        transformation.basename,
                    )
                    return
                result = function.execute(packet.payload, packet.partition_key, packet.input_index)
                for item in self._normalize_outputs(result):
                    self._enqueue_downstreams(transformation, packet.inherit_partition_info(item), instances)
                return

            if transformation_name == "CoMapTransformation":
                method = getattr(function, f"map{packet.input_index}")
                result = method(packet.payload)
                for item in self._normalize_outputs(result):
                    self._enqueue_downstreams(transformation, packet.inherit_partition_info(item), instances)
                return

            if transformation_name == "SinkTransformation":
                function.execute(packet.payload)
                return

            result = function.execute(packet.payload)
            for item in self._normalize_outputs(result):
                self._enqueue_downstreams(transformation, packet.inherit_partition_info(item), instances)
        finally:
            if function_ctx is not None and hasattr(function_ctx, "clear_key"):
                function_ctx.clear_key()

    def _run_replica_worker(
        self,
        transformation: Any,
        replica_index: int,
        work_queue: queue_module.Queue[Any],
        instances: dict[str, Any],
        stop_event: threading.Event,
    ) -> None:
        while True:
            item = work_queue.get()
            try:
                if item is _WORKER_STOP:
                    return
                self._process_packet(
                    transformation,
                    item,
                    instances,
                    replica_index=replica_index,
                )
            except Exception as exc:
                with self._dispatch_lock:
                    if self._worker_failure is None:
                        self._worker_failure = exc
                logger.exception(
                    "Worker replica %s[%d] failed during local execution.",
                    transformation.basename,
                    replica_index,
                )
                stop_event.set()
                return
            finally:
                work_queue.task_done()

    def _raise_if_worker_failed(self) -> None:
        if self._worker_failure is None:
            return
        raise RuntimeError("Local worker thread failed during pipeline execution.") from self._worker_failure

    def _wait_for_worker_drain(self) -> None:
        for replica_queues in self._worker_queues.values():
            for work_queue in replica_queues:
                work_queue.join()
        self._raise_if_worker_failed()

    def _shutdown_processing(
        self,
        instances: dict[str, Any],
        stop_event: threading.Event,
        *,
        wait_for_drain: bool,
    ) -> None:
        with self._worker_shutdown_lock:
            if self._worker_shutdown_started:
                return
            self._worker_shutdown_started = True

        stop_event.set()
        if wait_for_drain and self._worker_failure is None:
            self._wait_for_worker_drain()

        for replica_queues in self._worker_queues.values():
            for work_queue in replica_queues:
                work_queue.put(_WORKER_STOP)

        current_thread = threading.current_thread()
        for worker in self._worker_threads:
            if worker is current_thread:
                continue
            worker.join(timeout=30.0)

        self._finalize_functions(instances)
        self._raise_if_worker_failed()

    def _dispatch_from_source(
        self,
        source_transformation: Any,
        item: Any,
        instances: dict[str, Any],
    ) -> None:
        source_packet = Packet(payload=item)
        self._enqueue_downstreams(source_transformation, source_packet, instances)

    def _poll_source(
        self,
        transformation: Any,
        instances: dict[str, Any],
    ) -> tuple[str, Any | None]:
        with self._source_poll_lock_for(transformation):
            if transformation.basename in self._closed_sources:
                return ("closed", None)

            function = self._replicas_for(transformation, instances)[0]
            try:
                item = function.execute()
            except StopIteration:
                self._closed_sources.add(transformation.basename)
                return ("closed", None)

            if _is_batch_source(transformation):
                if _is_stop_signal(item):
                    self._closed_sources.add(transformation.basename)
                    return ("closed", None)
                return ("item", item)

            if _is_stream_source(transformation):
                if type(item).__name__ == "StopSignal":
                    self._closed_sources.add(transformation.basename)
                    return ("closed", None)
                if item is None:
                    return ("idle", None)
                return ("item", item)

            if _is_stop_signal(item):
                self._closed_sources.add(transformation.basename)
                return ("closed", None)
            return ("item", item)

    def _pump_stream_sources_once(self, instances: dict[str, Any]) -> bool:
        if self._worker_failure is not None:
            return False
        progressed = False
        for transformation in self.source_transformations:
            if not _is_stream_source(transformation):
                continue
            status, item = self._poll_source(transformation, instances)
            if status != "item" or item is None:
                continue
            progressed = True
            self._dispatch_from_source(transformation, item, instances)
        return progressed

    def _collect_source_items(self) -> list[tuple[Any, Any]]:
        instances = self._build_instances()
        active_sources = list(self.source_transformations)
        items: list[tuple[Any, Any]] = []

        while active_sources:
            next_active: list[Any] = []
            for transformation in active_sources:
                status, item = self._poll_source(transformation, instances)
                if status == "closed":
                    continue
                if status == "idle":
                    next_active.append(transformation)
                    continue
                items.append((transformation, item))
                next_active.append(transformation)
            active_sources = next_active

        logger.debug(
            "Collected %d source item(s) from %d source(s).",
            len(items),
            len(self.source_transformations),
        )
        return items

    def _finalize_functions(self, instances: dict[str, Any]) -> None:
        if self._finalized:
            return
        self._finalized = True

        for transformation in self.pipeline:
            if type(transformation).__name__ != "SinkTransformation":
                continue
            for function in self._replicas_for(transformation, instances):
                close = getattr(function, "close", None)
                if callable(close):
                    close()

        if self._service_runtime is not None:
            self._service_runtime.close()

    def submit(self, autostop: bool = False) -> Any:
        if autostop and self._can_submit_via_stage_ops():
            return self._submit_batch_via_stage_ops()
        if autostop:
            return self._submit_batch()
        return self._submit_streaming()

    def _execute_chain(self, items: list[Any], ops: list[tuple[str, Any]]) -> list[Any]:
        if not ops or not items:
            return items

        op_type, method_ref = ops[0]
        remaining = ops[1:]

        if op_type == _OP_SINK:
            for item in items:
                method_ref.call(item)
            return []

        if op_type == _OP_FLATMAP:
            next_items: list[Any] = []
            for item in items:
                result = method_ref.call(item)
                if result is None:
                    continue
                if hasattr(result, "__iter__") and not isinstance(result, (str, bytes)):
                    next_items.extend(result)
                else:
                    next_items.append(result)
            return self._execute_chain(next_items, remaining)

        if op_type == _OP_FILTER:
            next_items = [item for item in items if method_ref.call(item)]
            return self._execute_chain(next_items, remaining)

        next_items = [method_ref.call(item) for item in items]
        return self._execute_chain(next_items, remaining)

    def _execute_stage_ops_batch(self, items: list[Any], ops: list[tuple[str, Any]]) -> list[Any]:
        current_items = list(items)
        for op_type, method_ref in ops:
            if not current_items:
                return []

            futures = [method_ref.async_call(item) for item in current_items]

            if op_type == _OP_SINK:
                for future in futures:
                    future.result()
                return []

            results = [future.result() for future in futures]

            if op_type == _OP_FLATMAP:
                next_items: list[Any] = []
                for result in results:
                    if result is None:
                        continue
                    if hasattr(result, "__iter__") and not isinstance(result, (str, bytes, dict)):
                        next_items.extend(list(result))
                    else:
                        next_items.append(result)
                current_items = next_items
                continue

            if op_type == _OP_FILTER:
                current_items = [item for item, accepted in zip(current_items, results, strict=False) if accepted]
                continue

            current_items = results

        return current_items

    def _submit_batch_via_stage_ops(self) -> None:
        instances = self._build_instances()
        source_items = [item for _, item in self._collect_source_items()]

        try:
            if not source_items:
                logger.info("Source produced no items; batch pipeline skipped.")
                return None

            self._execute_stage_ops_batch(source_items, self.stage_ops)
            logger.info(
                "Processed %d item(s) through FlowNet actor stage ops from %d source(s).",
                len(source_items),
                len(self.source_transformations),
            )
            return None
        finally:
            self._cleanup_actor_handles()
            self._finalize_functions(instances)

    def _submit_batch(self) -> None:
        if not self.source_transformations:
            logger.info("Pipeline has no source transformations; batch pipeline skipped.")
            return []

        instances = self._build_instances()
        stop_event = threading.Event()
        self._start_worker_runtime(instances, stop_event)
        active_sources = list(self.source_transformations)
        processed_items = 0
        idle_rounds = 0
        should_drain = False

        try:
            while active_sources:
                self._raise_if_worker_failed()
                next_active: list[Any] = []
                emitted_in_round = False

                for transformation in active_sources:
                    self._raise_if_worker_failed()
                    status, item = self._poll_source(transformation, instances)
                    if status == "closed":
                        continue
                    if status == "idle":
                        next_active.append(transformation)
                        continue

                    emitted_in_round = True
                    processed_items += 1
                    next_active.append(transformation)
                    self._dispatch_from_source(transformation, item, instances)

                if not next_active:
                    break

                active_sources = next_active
                if emitted_in_round:
                    idle_rounds = 0
                    continue

                idle_rounds += 1
                if idle_rounds > 1000:
                    logger.warning(
                        "Stopping batch run after %d idle polling rounds with no new source items.",
                        idle_rounds,
                    )
                    break
                time.sleep(0.01)

            should_drain = True
            if processed_items == 0:
                logger.info("Source produced no items; batch pipeline skipped.")
                return None

            logger.info(
                "Processing batch of %d item(s) through pipeline from %d source(s).",
                processed_items,
                len(self.source_transformations),
            )
            return None
        finally:
            self._shutdown_processing(instances, stop_event, wait_for_drain=should_drain)

    def _mark_stream_source_closed(
        self,
        instances: dict[str, Any],
        stop_event: threading.Event,
    ) -> None:
        with self._dispatch_lock:
            if self._active_stream_sources > 0:
                self._active_stream_sources -= 1
            should_shutdown = self._active_stream_sources == 0

        if should_shutdown:
            self._shutdown_processing(
                instances,
                stop_event,
                wait_for_drain=self._worker_failure is None,
            )

    def _submit_streaming(self) -> _StreamingFlowHandle:
        stop_event = threading.Event()
        instances = self._build_instances()
        self._start_worker_runtime(instances, stop_event)
        source_threads: list[threading.Thread] = []
        self._active_stream_sources = len(self.source_transformations)

        for transformation in self.source_transformations:
            source_thread = threading.Thread(
                target=self._run_source_thread,
                args=(transformation, instances, stop_event),
                daemon=True,
                name=f"sage-source-{transformation.basename}",
            )
            source_thread.start()
            source_threads.append(source_thread)

        def shutdown_callback() -> None:
            self._shutdown_processing(
                instances,
                stop_event,
                wait_for_drain=self._worker_failure is None,
            )

        if not source_threads:
            shutdown_callback()

        return _StreamingFlowHandle(
            source_threads,
            worker_threads=self._worker_threads,
            stop_event=stop_event,
            shutdown_callback=shutdown_callback,
        )

    def _run_source_thread(
        self,
        transformation: Any,
        instances: dict[str, Any],
        stop_event: threading.Event,
    ) -> None:
        try:
            while not stop_event.is_set():
                if self._worker_failure is not None:
                    stop_event.set()
                    break
                status, item = self._poll_source(transformation, instances)
                if status == "closed":
                    break
                if status == "idle":
                    time.sleep(getattr(transformation, "delay", 0.01))
                    continue
                self._dispatch_from_source(transformation, item, instances)
        except Exception:
            logger.exception(
                "Source function '%s' raised an exception in streaming mode.",
                transformation.function_class.__name__,
            )
            stop_event.set()
        finally:
            logger.debug(
                "Source thread for '%s' exiting.",
                transformation.function_class.__name__,
            )
            self._mark_stream_source_closed(instances, stop_event)


class PipelineCompiler:
    def compile(self, pipeline: list[Any], adapter: Any) -> CompiledActorGraph:
        if not pipeline:
            raise ValueError(
                "PipelineCompiler.compile() received an empty pipeline. "
                "Build a pipeline with env.from_source(...).map(...).sink(...) before calling env.submit()."
            )

        source_trans: Any | None = None
        source_transforms: list[Any] = []
        proc_transformations: list[Any] = []

        for t in pipeline:
            _, op_type, _ = _classify(t)
            if op_type == "source":
                source_transforms.append(t)
                if source_trans is None:
                    source_trans = t
            else:
                proc_transformations.append(t)

        actor_handles: list[Any] = []
        stage_ops: list[tuple[str, Any]] = []
        downstream_edges: dict[str, list[tuple[Any, int]]] = {t.basename: [] for t in pipeline}

        for downstream in pipeline:
            for upstream in getattr(downstream, "upstreams", []):
                input_index = upstream.downstreams.get(downstream.basename, 0)
                downstream_edges.setdefault(upstream.basename, []).append((downstream, input_index))

        for t in proc_transformations:
            wrapper_cls, op_type, method_name = _classify(t)
            if not _uses_legacy_linear_wrapper(t):
                logger.debug(
                    "Compiled DAG-native stage %s [%s] without legacy linear wrapper.",
                    t.basename,
                    _transformation_name(t),
                )
                continue
            handle = adapter.create(
                wrapper_cls,
                t.function_class,
                *t.function_args,
                actor_config=_actor_config_for(t),
                **t.function_kwargs,
            )
            actor_handles.append(handle)
            method_ref = handle.get_method(method_name)
            stage_ops.append((op_type, method_ref))

            logger.debug(
                "Compiled stage %s → %s.%s() [op=%s]",
                t.basename,
                wrapper_cls.__name__,
                method_name,
                op_type,
            )

        return CompiledActorGraph(
            stage_ops=stage_ops,
            source_transformation=source_trans,
            actor_handles=actor_handles,
            adapter=adapter,
            source_transformations=source_transforms,
            pipeline=list(pipeline),
            downstream_edges=downstream_edges,
        )
