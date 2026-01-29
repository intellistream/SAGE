from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sage.common.core.functions.flatmap_function import FlatMapFunction


class HotspotPairListFlatten(FlatMapFunction):
    """把 SageFlowHotspotPairCoMap 输出的 list[pair] 扁平化为单条 pair。"""

    def execute(self, data: Any) -> Iterable[Any] | None:
        if data is None:
            return None
        if isinstance(data, list):
            return data
        return [data]
