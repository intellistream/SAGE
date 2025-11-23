"""Simple batch function classes for iterating over collections."""

from typing import Any, Iterator

from sage.common.core.functions import BatchFunction


class SimpleBatchIteratorFunction(BatchFunction):
    """
    Simple batch iterator function for collections (list, tuple).

    Args:
        data: List or tuple of items to iterate over
    """

    def __init__(self, data: list | tuple, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self._index = 0

    def execute(self) -> Any:
        """Execute the batch function - return next item or None when done."""
        if self._index >= len(self.data):
            return None
        item = self.data[self._index]
        self._index += 1
        return item

    def __iter__(self) -> Iterator[Any]:
        """Return an iterator over the data."""
        return iter(self.data)

    def __next__(self) -> Any:
        """Get the next item from the data."""
        if self._index >= len(self.data):
            raise StopIteration
        item = self.data[self._index]
        self._index += 1
        return item

    def __len__(self) -> int:
        """Return the length of the data."""
        return len(self.data)


class IterableBatchIteratorFunction(BatchFunction):
    """
    Batch iterator function for any iterable object.

    Args:
        iterable: Any iterable object to iterate over
        total_count: Optional total count of items (for progress tracking)
    """

    def __init__(self, iterable: Any, total_count: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self.iterable = iterable
        self.total_count = total_count
        self._iterator = None

    def execute(self) -> Any:
        """Execute the batch function - return next item or None when done."""
        if self._iterator is None:
            self._iterator = iter(self.iterable)
        try:
            return next(self._iterator)
        except StopIteration:
            return None

    def __iter__(self) -> Iterator[Any]:
        """Return an iterator over the iterable."""
        self._iterator = iter(self.iterable)
        return self._iterator

    def __next__(self) -> Any:
        """Get the next item from the iterable."""
        if self._iterator is None:
            self._iterator = iter(self.iterable)
        return next(self._iterator)

    def __len__(self) -> int:
        """Return the length if known, otherwise raise TypeError."""
        if self.total_count is not None:
            return self.total_count
        # Try to get length from the iterable
        try:
            return len(self.iterable)  # type: ignore[arg-type]
        except TypeError:
            raise TypeError(
                "IterableBatchIteratorFunction does not have a known length. "
                "Provide total_count parameter when creating the source."
            )
