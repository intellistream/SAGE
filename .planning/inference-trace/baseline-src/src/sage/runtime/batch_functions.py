"""Small batch-source helpers reclaimed into the main SAGE repository."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sage.foundation import BatchFunction


class SimpleBatchIteratorFunction(BatchFunction):
    """Iterate over a materialized collection such as ``list`` or ``tuple``."""

    def __init__(self, data: list | tuple, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self._index = 0

    def execute(self) -> Any:
        if self._index >= len(self.data):
            return None
        item = self.data[self._index]
        self._index += 1
        return item

    def __iter__(self) -> Iterator[Any]:
        return iter(self.data)

    def __next__(self) -> Any:
        if self._index >= len(self.data):
            raise StopIteration
        item = self.data[self._index]
        self._index += 1
        return item

    def __len__(self) -> int:
        return len(self.data)


class IterableBatchIteratorFunction(BatchFunction):
    """Iterate over any iterable object, optionally with a known total size."""

    def __init__(self, iterable: Any, total_count: int | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.iterable = iterable
        self.total_count = total_count
        self._iterator = None

    def execute(self) -> Any:
        if self._iterator is None:
            self._iterator = iter(self.iterable)
        try:
            return next(self._iterator)
        except StopIteration:
            return None

    def __iter__(self) -> Iterator[Any]:
        self._iterator = iter(self.iterable)
        return self._iterator

    def __next__(self) -> Any:
        if self._iterator is None:
            self._iterator = iter(self.iterable)
        return next(self._iterator)

    def __len__(self) -> int:
        if self.total_count is not None:
            return self.total_count
        try:
            return len(self.iterable)  # type: ignore[arg-type]
        except TypeError as exc:
            raise TypeError(
                "IterableBatchIteratorFunction does not have a known length. "
                "Provide total_count when creating the source."
            ) from exc


__all__ = ["SimpleBatchIteratorFunction", "IterableBatchIteratorFunction"]
