"""Demonstrate asynchronous clients calling a pipeline that is registered as a service.

This example reuses the decision pipeline service from
`hello_pipeline_as_service` but drives it with a client pipeline that submits
multiple requests concurrently using `call_service_async`.
"""

from __future__ import annotations

import random
import time
from typing import Any, Dict, List

try:
    from sage.common.core.functions.batch_function import BatchFunction
    from sage.common.core.functions.map_function import MapFunction
    from sage.common.core.functions.sink_function import SinkFunction
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.kernel.api.local_environment import LocalEnvironment
except ModuleNotFoundError:  # pragma: no cover - convenience for local runs
    import sys
    from pathlib import Path

    here = Path(__file__).resolve()
    repo_root = None
    for parent in here.parents:
        if (parent / "packages").exists():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError("Cannot locate SAGE repository root")

    for extra_path in [
        repo_root / "packages" / "sage" / "src",
        repo_root / "packages" / "sage-common" / "src",
        repo_root / "packages" / "sage-kernel" / "src",
        repo_root / "packages" / "sage-middleware" / "src",
        repo_root / "packages" / "sage-libs" / "src",
        repo_root / "packages" / "sage-tools" / "src",
    ]:
        sys.path.insert(0, str(extra_path))

    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.common.core.functions.batch_function import BatchFunction
    from sage.common.core.functions.map_function import MapFunction
    from sage.common.core.functions.sink_function import SinkFunction
    from sage.kernel.api.local_environment import LocalEnvironment

from hello_pipeline_as_service import (
    SHUTDOWN_MESSAGE,
    DecisionSink,
    FeatureEnrichment,
    FeatureStoreService,
    OrderPipelineService,
    RiskScoring,
    RiskScoringService,
    ServiceDrivenSource,
)
from pipeline_bridge import PipelineBridge

ASYNC_ORDERS: List[Dict[str, float | str | int]] = [
    {"order_id": "async-1001", "user_id": "user-101", "amount": 210.5, "latency": 0.6},
    {"order_id": "async-1002", "user_id": "user-102", "amount": 35.0, "latency": 0.2},
    {"order_id": "async-1003", "user_id": "user-103", "amount": 990.0, "latency": 0.9},
    {"order_id": "async-1004", "user_id": "user-104", "amount": 440.0, "latency": 0.4},
]


class SlowFeatureStoreService(FeatureStoreService):
    """Introduce variable latency to make concurrency observable."""

    def process(self, order: Dict[str, float | str | int]):
        delay = float(order.get("latency", 0.0))
        if delay > 0:
            time.sleep(delay)
        return super().process(order)  # type: ignore[arg-type]


class AsyncOrderSource(BatchFunction):
    """Emit the async orders and a final shutdown control message."""

    def __init__(self, orders: List[Dict[str, float | str | int]]):
        super().__init__()
        self._orders = list(orders) + [dict(SHUTDOWN_MESSAGE)]
        self._index = 0

    def execute(self):
        if self._index >= len(self._orders):
            return None

        order = self._orders[self._index]
        self._index += 1
        return order


class AsyncSubmit(MapFunction):
    """Submit orders asynchronously to the pipeline service."""

    def execute(self, order: Dict[str, float | str | int]):
        if order is None:
            return None

        if order.get("command") == "shutdown":
            response = self.call_service("order_pipeline", order, timeout=15.0)
            return {"type": "control", "order": order, "response": response}

        future = self.call_service_async("order_pipeline", order, timeout=20.0)
        return {"type": "future", "order": order, "future": future}


class AwaitDecision(MapFunction):
    """Await the decision from futures produced by `AsyncSubmit`."""

    def execute(self, record: Dict[str, Any]):
        if record is None:
            return None

        if record.get("type") == "control":
            return record

        future = record.get("future")
        if future is None:
            return None

        decision = future.result(timeout=20.0)
        return {"type": "decision", "order": record["order"], "decision": decision}


class AsyncResultSink(SinkFunction):
    """Print the order decisions along with latency info."""

    def execute(self, payload: Dict[str, Any]):
        if payload is None:
            return None

        if payload.get("type") == "decision":
            order = payload["order"]
            decision = payload["decision"]
            print(
                f"[Async Driver] Order {order['order_id']} (latency={order.get('latency', 0)}s)\n"
                f"    => decision={decision['recommendation']}, risk={decision['risk_score']}",
                flush=True,
            )
        else:
            print("[Async Driver] Pipeline shutdown acknowledged", flush=True)

        return payload


def main():
    env = LocalEnvironment("pipeline_as_service_async")
    bridge = PipelineBridge()

    env.register_service("feature_store", SlowFeatureStoreService)
    env.register_service("risk_scoring", RiskScoringService)
    env.register_service("order_pipeline", OrderPipelineService, bridge)

    (
        env.from_source(ServiceDrivenSource, bridge)
        .map(FeatureEnrichment)
        .map(RiskScoring)
        .sink(DecisionSink)
    )

    (
        env.from_batch(AsyncOrderSource, ASYNC_ORDERS)
        .map(AsyncSubmit)
        .map(AwaitDecision)
        .sink(AsyncResultSink)
    )

    env.submit(autostop=True)


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    random.seed(42)
    main()
