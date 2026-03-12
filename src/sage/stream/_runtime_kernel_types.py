"""Main-repo owned runtime data structures used by in-tree stream execution."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from sage.foundation import CustomLogger


@dataclass(slots=True)
class StopSignal:
    """Sentinel payload that marks the end of a stream or batch source."""

    name: str
    source: str | None = None
    timestamp: int = field(default_factory=time.time_ns)


class Packet:
    """Lightweight packet carrying payload plus optional partition metadata."""

    def __init__(
        self,
        payload: Any,
        input_index: int = 0,
        partition_key: Any = None,
        partition_strategy: str | None = None,
    ) -> None:
        self.payload = payload
        self.input_index = input_index
        self.partition_key = partition_key
        self.partition_strategy = partition_strategy
        self.timestamp = time.time_ns()

    def is_keyed(self) -> bool:
        return self.partition_key is not None

    def inherit_partition_info(self, new_payload: Any) -> Packet:
        return Packet(
            payload=new_payload,
            input_index=self.input_index,
            partition_key=self.partition_key,
            partition_strategy=self.partition_strategy,
        )

    def update_key(self, new_key: Any, new_strategy: str | None = None) -> Packet:
        return Packet(
            payload=self.payload,
            input_index=self.input_index,
            partition_key=new_key,
            partition_strategy=new_strategy or self.partition_strategy,
        )

    def copy(self) -> Packet:
        packet = Packet(
            payload=self.payload,
            input_index=self.input_index,
            partition_key=self.partition_key,
            partition_strategy=self.partition_strategy,
        )
        packet.timestamp = self.timestamp
        return packet

    def __repr__(self) -> str:
        key_info = f"key={self.partition_key}" if self.is_keyed() else "unkeyed"
        payload_type = type(self.payload).__name__ if self.payload is not None else "None"
        return (
            f"<Packet input={self.input_index} {key_info} "
            f"payload_type={payload_type} ts={self.timestamp}>"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Packet):
            return False
        return (
            self.payload == other.payload
            and self.input_index == other.input_index
            and self.partition_key == other.partition_key
            and self.partition_strategy == other.partition_strategy
        )


class InMemoryRouter:
    """Small in-process router used by main-repo owned operators and tests."""

    def __init__(self, ctx: TaskContext | None = None) -> None:
        self.ctx = ctx
        self._targets: list[Any] = []

    def add_target(self, target: Any) -> None:
        self._targets.append(target)

    def clear_all_connections(self) -> None:
        self._targets.clear()

    @property
    def input_count(self) -> int:
        return max(1, len(self._targets))

    def send(self, packet: Packet) -> bool:
        if not self._targets:
            return False
        delivered = False
        for target in self._targets:
            if hasattr(target, "receive_packet"):
                target.receive_packet(packet)
                delivered = True
            elif hasattr(target, "put"):
                target.put(packet)
                delivered = True
            elif callable(target):
                target(packet)
                delivered = True
        return delivered

    def send_stop_signal(self, stop_signal: StopSignal) -> None:
        for target in self._targets:
            if hasattr(target, "receive_packet"):
                target.receive_packet(Packet(stop_signal))
            elif hasattr(target, "put"):
                target.put(stop_signal)
            elif callable(target):
                target(stop_signal)

    def get_connections_info(self) -> dict[str, Any]:
        return {"targets": len(self._targets)}


class TaskContext:
    """Minimal in-tree task context required by the operator surface."""

    def __init__(
        self,
        name: str = "task",
        *,
        env_name: str = "local",
        router: InMemoryRouter | None = None,
        stop_callback: Any | None = None,
    ) -> None:
        self.name = name
        self.env_name = env_name
        self.env_base_dir: str | None = None
        self.env_uuid: str | None = None
        self.env_console_log_level = "INFO"
        self.parallel_index = 0
        self.parallelism = 1
        self.is_spout = False
        self.delay = 0.01
        self.stop_signal_num = 1
        self.jobmanager_host = "127.0.0.1"
        self.jobmanager_port = 0
        self.input_qd: Any | None = None
        self.response_qd: Any | None = None
        self.service_qds: dict[str, Any] = {}
        self.downstream_qds: list[list[Any]] | None = None
        self._logger = CustomLogger(name=name)
        self._router = router or InMemoryRouter(self)
        self._stop_event: threading.Event | None = None
        self._current_packet_key: Any = None
        self._stop_callback = stop_callback

    @property
    def logger(self) -> CustomLogger:
        return self._logger

    @property
    def router(self) -> InMemoryRouter:
        return self._router

    @property
    def stop_event(self) -> threading.Event:
        if self._stop_event is None:
            self._stop_event = threading.Event()
        return self._stop_event

    def set_current_key(self, key: Any) -> None:
        self._current_packet_key = key

    def clear_key(self) -> None:
        self._current_packet_key = None

    def send_packet(self, packet: Packet) -> bool:
        return self.router.send(packet)

    def send_stop_signal(self, stop_signal: StopSignal) -> None:
        self.router.send_stop_signal(stop_signal)

    def get_routing_info(self) -> dict[str, Any]:
        return self.router.get_connections_info()

    def set_stop_signal(self) -> None:
        self.stop_event.set()

    def is_stop_requested(self) -> bool:
        return self.stop_event.is_set()

    def clear_stop_signal(self) -> None:
        self.stop_event.clear()

    def request_stop(self) -> None:
        self.send_stop_signal_back(self.name)

    def send_stop_signal_back(self, node_name: str) -> None:
        if callable(self._stop_callback):
            self._stop_callback(node_name)

    def handle_stop_signal(self, signal: StopSignal) -> bool:
        self.request_stop()
        self.send_stop_signal(signal)
        return True

    def set_input_queue_descriptor(self, descriptor: Any) -> None:
        self.input_qd = descriptor

    def get_input_queue_descriptor(self) -> Any:
        return self.input_qd

    def set_service_response_queue_descriptor(self, descriptor: Any) -> None:
        self.response_qd = descriptor

    def get_service_response_queue_descriptor(self) -> Any:
        return self.response_qd

    def set_upstream_queue_descriptors(self, descriptors: dict[int, list[Any]]) -> None:
        self.upstream_qds = descriptors

    def get_upstream_queue_descriptors(self) -> dict[int, list[Any]] | None:
        return getattr(self, "upstream_qds", None)

    def set_downstream_queue_descriptors(self, descriptors: list[list[Any]]) -> None:
        self.downstream_qds = descriptors

    def get_downstream_queue_descriptors(self) -> list[list[Any]] | None:
        return self.downstream_qds

    def set_service_request_queue_descriptors(self, descriptors: dict[str, Any]) -> None:
        self.service_qds = descriptors

    def get_service_request_queue_descriptors(self) -> dict[str, Any]:
        return self.service_qds

    def get_service(self, service_name: str) -> Any:
        raise RuntimeError(f"Service '{service_name}' is not available in the lightweight context")

    def call_service(self, service_name: str, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"Service '{service_name}' is not available in the lightweight context")

    def call_service_async(self, service_name: str, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"Service '{service_name}' is not available in the lightweight context")

    def cleanup(self) -> None:
        self.router.clear_all_connections()


class BaseTask:
    """Minimal in-tree task abstraction used by source operators."""

    def __init__(self, ctx: TaskContext) -> None:
        self.ctx = ctx
        self.is_running = False


__all__ = ["BaseTask", "InMemoryRouter", "Packet", "StopSignal", "TaskContext"]
