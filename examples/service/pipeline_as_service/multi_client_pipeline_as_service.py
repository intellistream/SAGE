"""Multiple driver pipelines sharing a single pipeline-as-a-service endpoint.

This example demonstrates how different segments (new users vs returning users)
can call the same pipeline service concurrently while sharing supporting
services.
"""

from __future__ import annotations

from typing import Any, Dict, List

try:
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.core.api.function.sink_function import SinkFunction
    from sage.core.api.local_environment import LocalEnvironment
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
    from sage.core.api.function.sink_function import SinkFunction
    from sage.core.api.local_environment import LocalEnvironment

from hello_pipeline_as_service import (
    DecisionSink,
    FeatureEnrichment,
    FeatureStoreService,
    InvokePipeline,
    OrderPipelineService,
    OrderSource,
    RiskScoring,
    RiskScoringService,
    ServiceDrivenSource,
)
from pipeline_bridge import PipelineBridge

NEW_USER_ORDERS: List[Dict[str, float | str]] = [
    {"order_id": "multi-new-001", "user_id": "user-new-01", "amount": 29.99},
    {"order_id": "multi-new-002", "user_id": "user-new-02", "amount": 59.0},
]

RETURNING_USER_ORDERS: List[Dict[str, float | str]] = [
    {"order_id": "multi-ret-001", "user_id": "user-ret-01", "amount": 330.0},
    {"order_id": "multi-ret-002", "user_id": "user-ret-02", "amount": 87.5},
]


class SegmentedOrderSource(OrderSource):
    """Extend the base OrderSource to tag orders with a segment name."""

    def __init__(
        self,
        orders: List[Dict[str, float | str]],
        segment: str,
        *,
        include_shutdown: bool = False,
    ):
        super().__init__(orders, include_shutdown=include_shutdown)
        self._segment = segment

    def execute(self):
        record = super().execute()
        if record is None:
            return None

        if record.get("command") == "shutdown":
            return record

        tagged = dict(record)
        tagged["segment"] = self._segment
        return tagged


class SegmentedDriverSink(SinkFunction):
    """Print results grouped by segment."""

    def execute(self, payload: Dict[str, Any]):
        if payload is None:
            return None

        if payload.get("type") == "decision":
            order = payload["order"]
            decision = payload["decision"]
            print(
                f"[Multi Driver] segment={order.get('segment', 'unknown')} order={order['order_id']}"
                f" => recommendation={decision['recommendation']} risk={decision['risk_score']}",
                flush=True,
            )
        else:
            print("[Multi Driver] Pipeline shutdown acknowledged", flush=True)

        return payload


def main():
    env = LocalEnvironment("pipeline_as_service_multi_client")
    bridge = PipelineBridge()

    env.register_service("feature_store", FeatureStoreService)
    env.register_service("risk_scoring", RiskScoringService)
    env.register_service("order_pipeline", OrderPipelineService, bridge)

    (
        env.from_source(ServiceDrivenSource, bridge)
        .map(FeatureEnrichment)
        .map(RiskScoring)
        .sink(DecisionSink)
    )

    (
        env.from_batch(
            SegmentedOrderSource,
            NEW_USER_ORDERS,
            segment="new_users",
            include_shutdown=False,
        )
        .map(InvokePipeline)
        .sink(SegmentedDriverSink)
    )

    (
        env.from_batch(
            SegmentedOrderSource,
            RETURNING_USER_ORDERS,
            segment="returning_users",
            include_shutdown=True,
        )
        .map(InvokePipeline)
        .sink(SegmentedDriverSink)
    )

    env.submit(autostop=True)


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
