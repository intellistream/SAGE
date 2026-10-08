"""Runtime-agnostic actor wrappers for the in-tree streaming compiler."""

from __future__ import annotations

from typing import Any

from sage.foundation import Collector

__all__ = [
    "SourceActorWrapper",
    "MapActorWrapper",
    "FlatMapActorWrapper",
    "FilterActorWrapper",
    "SinkActorWrapper",
    "ServiceActorWrapper",
]


class SourceActorWrapper:
    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def run(self, trigger: Any = None) -> Any:
        return self._fn.execute(trigger)


class MapActorWrapper:
    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def process(self, item: Any) -> Any:
        return self._fn.execute(item)


class FlatMapActorWrapper:
    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def process(self, item: Any) -> list[Any]:
        collector = Collector(logger=getattr(self._fn, "logger", None))
        if hasattr(self._fn, "insert_collector"):
            self._fn.insert_collector(collector)

        result = self._fn.execute(item)
        if result is not None:
            return list(result)
        return collector.get_collected_data()


class FilterActorWrapper:
    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def accepts(self, item: Any) -> bool:
        return bool(self._fn.execute(item))


class SinkActorWrapper:
    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def consume(self, item: Any) -> None:
        self._fn.execute(item)


class ServiceActorWrapper:
    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def process(self, item: Any) -> Any:
        return self._fn.execute(item)
