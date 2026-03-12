"""Main-repo owned lightweight pipeline compiler for runtime-backed execution."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

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


def _is_stop_signal(item: Any) -> bool:
    return item is None or type(item).__name__ == "StopSignal"


class _StreamingFlowHandle:
    def __init__(
        self, source_thread: threading.Thread | None, *, stop_event: threading.Event
    ) -> None:
        self._thread = source_thread
        self._stop_event = stop_event

    def stop(self, timeout: float = 30.0) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


@dataclass
class CompiledActorGraph:
    stage_ops: list[tuple[str, Any]]
    source_transformation: Any | None
    actor_handles: list[Any] = field(default_factory=list)
    adapter: Any = None

    def submit(self, autostop: bool = False) -> Any:
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

    def _collect_source_items(self) -> list[Any]:
        t = self.source_transformation
        if t is None:
            return []

        fn = t.function_class(*t.function_args, **t.function_kwargs)
        items: list[Any] = []
        while True:
            item = fn.execute()
            if _is_stop_signal(item):
                break
            items.append(item)

        logger.debug(
            "Source '%s' drained: %d items collected.", t.function_class.__name__, len(items)
        )
        return items

    def _submit_batch(self) -> None:
        items = self._collect_source_items()
        if not items:
            logger.info("Source produced no items; batch pipeline skipped.")
            return None

        logger.info("Processing batch of %d items through pipeline.", len(items))
        for item in items:
            self._execute_chain([item], self.stage_ops)
        return None

    def _submit_streaming(self) -> _StreamingFlowHandle:
        stop_event = threading.Event()
        source_thread: threading.Thread | None = None

        if self.source_transformation is not None:
            source_thread = threading.Thread(
                target=self._run_source_thread,
                args=(stop_event,),
                daemon=True,
                name=f"sage-source-{self.source_transformation.basename}",
            )
            source_thread.start()

        return _StreamingFlowHandle(source_thread, stop_event=stop_event)

    def _run_source_thread(self, stop_event: threading.Event) -> None:
        t = self.source_transformation
        fn = t.function_class(*t.function_args, **t.function_kwargs)

        try:
            while not stop_event.is_set():
                item = fn.execute()
                if _is_stop_signal(item):
                    break
                self._execute_chain([item], self.stage_ops)
        except Exception:
            logger.exception(
                "Source function '%s' raised an exception in streaming mode.",
                t.function_class.__name__,
            )
        finally:
            logger.debug("Source thread for '%s' exiting.", t.function_class.__name__)


class PipelineCompiler:
    def compile(self, pipeline: list[Any], adapter: Any) -> CompiledActorGraph:
        if not pipeline:
            raise ValueError(
                "PipelineCompiler.compile() received an empty pipeline. "
                "Build a pipeline with env.from_source(...).map(...).sink(...) before calling env.submit()."
            )

        source_trans: Any | None = None
        proc_transformations: list[Any] = []

        for t in pipeline:
            _, op_type, _ = _classify(t)
            if op_type == "source":
                if source_trans is not None:
                    raise ValueError(
                        "PipelineCompiler found more than one SourceTransformation in the pipeline. "
                        "Only a single source is supported per compilation unit."
                    )
                source_trans = t
            else:
                proc_transformations.append(t)

        actor_handles: list[Any] = []
        stage_ops: list[tuple[str, Any]] = []

        for t in proc_transformations:
            wrapper_cls, op_type, method_name = _classify(t)
            handle = adapter.create(
                wrapper_cls,
                t.function_class,
                *t.function_args,
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
        )
