"""Pipeline-as-Service demo

This example shows how a SAGE pipeline can be registered as a service and then
invoked through the unified ``call_service`` helpers. The pipeline listens for
requests coming from the service layer, enriches them via other services, and
replies with a structured decision payload.
"""

from __future__ import annotations

import math
import queue
import random
import time
from typing import Any, Dict, List

# Try regular imports first; fall back to repo-relative paths when running
# directly from the source tree without installing the package.
try:
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.kernel.api.function.batch_function import BatchFunction
    from sage.kernel.api.function.map_function import MapFunction
    from sage.kernel.api.function.sink_function import SinkFunction
    from sage.kernel.api.function.source_function import SourceFunction
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.kernel.api.service.base_service import BaseService
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
    from sage.kernel.api.function.batch_function import BatchFunction
    from sage.kernel.api.function.map_function import MapFunction
    from sage.kernel.api.function.sink_function import SinkFunction
    from sage.kernel.api.function.source_function import SourceFunction
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.kernel.api.service.base_service import BaseService

from pipeline_bridge import PipelineBridge, PipelinePayload
from sage.kernel.runtime.communication.router.packet import StopSignal

ORDERS: List[Dict[str, str]] = [
    {"order_id": "o-1001", "user_id": "user-001", "amount": 129.9},
    {"order_id": "o-1002", "user_id": "user-002", "amount": 59.0},
    {"order_id": "o-1003", "user_id": "user-003", "amount": 450.5},
]

SHUTDOWN_MESSAGE = {"command": "shutdown"}


class ServiceDrivenSource(SourceFunction):
    """Source operator that pulls requests from the service bridge."""

    def __init__(self, bridge: PipelineBridge, poll_interval: float = 0.1):
        super().__init__()
        self._bridge = bridge
        self._poll_interval = poll_interval

    def execute(self, data=None):
        request = self._bridge.next(timeout=self._poll_interval)
        if request is None:
            return None

        if isinstance(request, StopSignal):
            return request

        return PipelinePayload(
            order=request.payload, response_queue=request.response_queue
        )


class OrderSource(BatchFunction):
    """Emit a fixed list of orders as the batch source."""

    def __init__(self, orders: List[Dict[str, str]], *, include_shutdown: bool = True):
        super().__init__()
        self._orders = list(orders)
        if include_shutdown:
            self._orders.append(dict(SHUTDOWN_MESSAGE))
        self._index = 0

    def execute(self, data=None):
        if self._index >= len(self._orders):
            return None

        order = self._orders[self._index]
        self._index += 1
        return order


class FeatureStoreService(BaseService):
    """Simple feature store that returns per-user aggregates."""

    def __init__(self):
        super().__init__()
        self._user_features = {
            "user-001": {"successful_orders": 5, "chargeback_ratio": 0.01},
            "user-002": {"successful_orders": 2, "chargeback_ratio": 0.08},
            "user-003": {"successful_orders": 12, "chargeback_ratio": 0.0},
        }

    def process(self, order: Dict[str, str]):
        """Default entry point leveraged by pipeline-as-service calls."""

        features = self._user_features.get(
            order["user_id"], {"successful_orders": 0, "chargeback_ratio": 0.5}
        )
        features = dict(features)  # shallow copy for isolation
        features["order_amount"] = order["amount"]
        features["feature_timestamp"] = time.time()
        return features


class FeatureEnrichment(MapFunction):
    """Use the feature store service without specifying the method name."""

    def execute(self, payload: PipelinePayload):
        if payload is None:
            return None

        order = payload.order
        features = self.call_service("feature_store", order)
        enriched = {**order, "features": features}
        feature_keys = ", ".join(sorted(features.keys()))
        self.logger.info(
            f"Enriched order {order.get('order_id', '<control>')} with feature keys [{feature_keys}]"
        )
        payload.features = features
        payload.enriched = enriched
        return payload


class RiskScoringService(BaseService):
    """Trivial risk-scoring service with a `process` entry point."""

    def process(self, enriched_order: Dict[str, str]):
        features = enriched_order.get("features", {})
        amount = float(enriched_order.get("amount", 0.0))
        chargeback_ratio = float(features.get("chargeback_ratio", 0.0))
        history = float(features.get("successful_orders", 0.0))

        base_score = 0.4 * chargeback_ratio + 0.0005 * amount
        history_modifier = 0.2 if history > 5 else 0.0
        jitter = random.uniform(-0.05, 0.05)

        risk = min(max(base_score - history_modifier + jitter, 0.0), 1.0)
        recommendation = "manual_review" if risk > 0.4 else "auto_approve"

        return {
            "risk_score": round(risk, 3),
            "recommendation": recommendation,
            "generated_at": time.time(),
        }


class RiskScoring(MapFunction):
    """Invoke the risk scoring service asynchronously."""

    def execute(self, payload: PipelinePayload):
        if payload is None:
            return None

        enriched_order = payload.enriched or payload.order
        future = self.call_service_async("risk_scoring", enriched_order)
        scoring = future.result(timeout=10.0)
        payload.scoring = scoring
        payload.enriched = {**enriched_order, "scoring": scoring}

        self.logger.info(
            f"Scored order {enriched_order.get('order_id', '<control>')} with risk {scoring['risk_score']:.3f}"
        )
        return payload


class DecisionSink(SinkFunction):
    """Final sink that prints a human-readable decision."""

    def execute(self, payload: PipelinePayload):
        if payload is None:
            return None

        scoring = payload.scoring or {}
        enriched_order = payload.enriched or payload.order
        order_id = enriched_order.get("order_id", "<control>")
        decision = scoring.get("recommendation", "unknown")
        risk = scoring.get("risk_score", math.nan)

        result = {
            "order_id": order_id,
            "recommendation": decision,
            "risk_score": risk,
            "generated_at": scoring.get("generated_at", time.time()),
            "features": payload.features or {},
        }

        try:
            payload.response_queue.put(result, timeout=5.0)
        except queue.Full:  # pragma: no cover - defensive guard
            self.logger.error(
                "Failed to publish decision for order %s because response queue is full",
                order_id,
            )

        print(
            f"[Pipeline] Order {order_id} => decision={decision}, risk={risk}",
            flush=True,
        )
        return result


class OrderPipelineService(BaseService):
    """Expose the decision pipeline itself as a service."""

    def __init__(self, bridge: PipelineBridge, request_timeout: float = 15.0):
        super().__init__()
        self._bridge = bridge
        self._request_timeout = request_timeout

    def process(self, message: Dict[str, Any]):
        if message is None:
            raise ValueError("Pipeline service received an empty message")

        if message.get("command") == "shutdown":
            self._bridge.close()
            return {"status": "shutdown_requested"}

        try:
            response_queue = self._bridge.submit(message)
        except RuntimeError as exc:
            raise RuntimeError("Pipeline service is shutting down") from exc

        try:
            return response_queue.get(timeout=self._request_timeout)
        except queue.Empty as exc:
            raise TimeoutError(
                "Pipeline service timed out waiting for a reply"
            ) from exc


class InvokePipeline(MapFunction):
    """Driver operator that calls the pipeline service for each order."""

    def execute(self, payload: Dict[str, Any]):
        if payload is None:
            return None

        response = self.call_service("order_pipeline", payload, timeout=20.0)

        if payload.get("command") == "shutdown":
            self.logger.info("Pipeline shutdown acknowledged: %s", response)
            return {"type": "control", "ack": response}

        return {"type": "decision", "order": payload, "decision": response}


class DriverSink(SinkFunction):
    """Display results returned from the pipeline service caller."""

    def execute(self, payload: Dict[str, Any]):
        if payload is None:
            return None

        if payload.get("type") == "decision":
            order = payload["order"]
            decision = payload["decision"]
            print(
                f"[Driver] Order {order['order_id']} => decision={decision['recommendation']}, risk={decision['risk_score']}",
                flush=True,
            )
        else:
            print("[Driver] Pipeline shutdown request completed", flush=True)

        return payload


def main():
    env = LocalEnvironment("pipeline_as_service_demo")
    bridge = PipelineBridge()

    # Register services exposing a default `process` entry point.
    env.register_service("feature_store", FeatureStoreService)
    env.register_service("risk_scoring", RiskScoringService)
    env.register_service("order_pipeline", OrderPipelineService, bridge)

    (
        env.from_source(ServiceDrivenSource, bridge)
        .map(FeatureEnrichment)
        .map(RiskScoring)
        .sink(DecisionSink)
    )

    (env.from_batch(OrderSource, ORDERS).map(InvokePipeline).sink(DriverSink))

    env.submit(autostop=True)


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
