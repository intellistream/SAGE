"""Main-repo owned operator layer for SAGE streams.

These operators still execute on top of the existing kernel runtime task/context
implementation, but the public stream/operator surface is now owned in-tree.
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from sage.foundation import BaseFunction, Collector, FlatMapFunction

from ._runtime_kernel_types import Packet, StopSignal
from .factories import FunctionFactory

if TYPE_CHECKING:
    from sage.foundation import CustomLogger

    from ._runtime_kernel_types import BaseTask, TaskContext


__all__ = [
    "BaseOperator",
    "MapOperator",
    "FilterOperator",
    "FlatMapOperator",
    "SinkOperator",
    "SourceOperator",
    "BatchOperator",
    "KeyByOperator",
    "JoinOperator",
    "CoMapOperator",
    "FutureOperator",
]


class BaseOperator(ABC):
    __state_include__: list[str] = []
    __state_exclude__: list[str] = ["ctx", "function", "logger", "_logger"]

    def __init__(self, function_factory: FunctionFactory, ctx: TaskContext, *args, **kwargs):
        self.ctx: TaskContext = ctx
        self.function: BaseFunction
        try:
            self.function = function_factory.create_function(self.name, ctx)
            self.logger.debug(f"Created function instance with {function_factory}")
        except Exception as exc:
            self.logger.error(f"Failed to create function instance: {exc}", exc_info=True)
            raise

    def send_packet(self, packet: Packet) -> bool:
        return self.ctx.send_packet(packet)  # type: ignore[return-value]

    def send_stop_signal(self, stop_signal: StopSignal) -> None:
        self.ctx.send_stop_signal(stop_signal)

    def get_routing_info(self) -> dict[str, Any]:
        return self.ctx.get_routing_info()

    @property
    def router(self):
        return self.ctx.router

    def receive_packet(self, packet: Packet):
        if packet is None:
            self.logger.warning(f"Received None packet in {self.name}")
            return
        self.logger.debug(f"Operator {self.name} received packet: {packet}")
        try:
            self.ctx.set_current_key(packet.partition_key)
            self.process_packet(packet)
        finally:
            self.ctx.clear_key()

    @abstractmethod
    def process_packet(self, packet: Packet | None = None):
        return

    def restore_state(self, state: dict[str, Any]):
        if "function_state" in state and hasattr(self.function, "restore_state"):
            try:
                self.function.restore_state(state["function_state"])
            except Exception as exc:
                self.logger.warning(f"Failed to restore function state: {exc}")
        if "operator_attrs" in state:
            for attr_name, value in state["operator_attrs"].items():
                try:
                    setattr(self, attr_name, value)
                except Exception as exc:
                    self.logger.warning(
                        f"Failed to restore operator attribute '{attr_name}': {exc}"
                    )

    @property
    def name(self) -> str:
        return self.ctx.name

    @property
    def logger(self) -> CustomLogger:
        return self.ctx.logger


class MapOperator(BaseOperator):
    def __init__(
        self,
        function_factory: FunctionFactory,
        ctx: TaskContext,
        enable_profile: bool = False,
        *args,
        **kwargs,
    ):
        kwargs.pop("enable_profile", None)
        super().__init__(function_factory, ctx, *args, **kwargs)
        self.enable_profile = enable_profile
        if self.enable_profile:
            self._setup_time_tracking()

    def _setup_time_tracking(self):
        if hasattr(self.ctx, "env_base_dir") and self.ctx.env_base_dir:
            self.time_base_path = os.path.join(
                self.ctx.env_base_dir, ".sage_states", "time_records"
            )
        else:
            self.time_base_path = os.path.join(os.getcwd(), ".sage_states", "time_records")
        os.makedirs(self.time_base_path, exist_ok=True)
        self.time_records = []

    def _save_time_record(self, duration: float):
        if not self.enable_profile:
            return
        self.time_records.append(
            {
                "timestamp": time.time(),
                "duration": duration,
                "function_name": self.function.__class__.__name__,
                "operator_name": self.name,
            }
        )
        self._persist_time_records()

    def _persist_time_records(self):
        if not self.enable_profile or not self.time_records:
            return
        filename = f"time_records_{int(time.time())}.json"
        path = os.path.join(self.time_base_path, filename)
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.time_records, handle, ensure_ascii=False, indent=2)
            self.time_records = []
        except Exception as exc:
            self.logger.error(f"Failed to persist time records: {exc}")

    def process_packet(self, packet: Packet | None = None):
        try:
            if packet is None or packet.payload is None:
                self.logger.warning(f"Operator {self.name} received empty data")
                return
            if isinstance(packet.payload, StopSignal):
                self.logger.debug(f"Operator {self.name} received StopSignal, propagating...")
                self.router.send(packet)
                return

            start_time = time.time()
            result = self.function.execute(packet.payload)
            duration = time.time() - start_time
            if self.enable_profile:
                self._save_time_record(duration)

            if isinstance(result, dict):
                operator_name = self.function.__class__.__name__
                if "Retriever" in operator_name or "Retrieve" in operator_name:
                    result["retrieve_time"] = duration
                elif "Refiner" in operator_name or "Refine" in operator_name:
                    result["refine_time"] = duration
                elif "Generator" in operator_name or "Generate" in operator_name:
                    result["generate_time"] = duration

            result_packet = packet.inherit_partition_info(result) if result is not None else None
            if result_packet is not None:
                self.router.send(result_packet)
        except Exception as exc:
            self.logger.error(f"Error in {self.name}.process(): {exc}", exc_info=True)

    def __del__(self):
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_time_records()
            except Exception:
                pass


class FilterOperator(BaseOperator):
    def process_packet(self, packet: Packet | None = None):
        try:
            if packet is None or packet.payload is None:
                self.logger.debug(f"FilterOperator {self.name}: Received empty packet")
                return
            should_pass = self.function.execute(packet.payload)
            if should_pass:
                self.router.send(packet)
        except Exception as exc:
            self.logger.error(f"Error in FilterOperator {self.name}: {exc}", exc_info=True)


class FlatMapOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out: Collector = Collector(logger=self.logger)
        if isinstance(self.function, FlatMapFunction):
            self.function.insert_collector(self.out)

    def process_packet(self, packet: Packet | None = None):
        try:
            if packet is None or packet.payload is None:
                return
            if isinstance(packet.payload, StopSignal):
                self.router.send(packet)
                return
            self.out.clear()
            result = self.function.execute(packet.payload)
            if result is not None:
                self._flatmap_send(result, packet)
            for item_data in self.out.get_collected_data():
                self.router.send(packet.inherit_partition_info(item_data))
            self.out.clear()
        except Exception as exc:
            self.logger.error(
                f"Error in FlatMapOperator '{self.name}'.process_packet(): {exc}",
                exc_info=True,
            )

    def _flatmap_send(self, result: Any, source_packet: Packet):
        if hasattr(result, "__iter__") and not isinstance(result, (str, bytes)):
            for item in result:
                self.router.send(source_packet.inherit_partition_info(item))
        else:
            self.router.send(source_packet.inherit_partition_info(result))


class SinkOperator(BaseOperator):
    def process_packet(self, packet: Packet | None = None):
        try:
            if packet is None or packet.payload is None:
                self.logger.warning(f"Operator {self.name} received empty data")
                return
            if isinstance(packet.payload, StopSignal):
                return
            self.function.execute(packet.payload)
        except Exception as exc:
            self.logger.error(f"Error in {self.name}.process(): {exc}", exc_info=True)

    def handle_stop_signal(self):
        try:
            if hasattr(self.function, "close") and callable(self.function.close):  # type: ignore[attr-defined]
                self.function.close()  # type: ignore[attr-defined]
        except Exception as exc:
            self.logger.error(f"Error in {self.name}.handle_stop_signal(): {exc}", exc_info=True)


class SourceOperator(BaseOperator):
    task: BaseTask | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_signal_sent = False
        self.task = None

    def receive_packet(self, packet: Packet):
        self.process_packet(packet)

    def process_packet(self, packet: Packet | None = None):
        result = self.function.execute()
        if isinstance(result, StopSignal):
            if self._stop_signal_sent:
                return
            self._stop_signal_sent = True
            result.source = self.name
            self.router.send_stop_signal(result)
            if hasattr(self.ctx, "request_stop"):
                self.ctx.request_stop()
            if self.task is not None:
                if hasattr(self.task.ctx, "set_stop_signal"):
                    self.task.ctx.set_stop_signal()
                if hasattr(self.task, "is_running"):
                    self.task.is_running = False
            return
        if result is not None:
            success = self.router.send(Packet(result))
            if not success:
                if not self._stop_signal_sent:
                    self._stop_signal_sent = True
                    stop_signal = StopSignal(f"{self.name}-send-failed")
                    self.router.send_stop_signal(stop_signal)
                    if hasattr(self.ctx, "request_stop"):
                        self.ctx.request_stop()
                if self.task is not None:
                    self.task.ctx.set_stop_signal()
                    self.task.is_running = False


class BatchOperator(BaseOperator):
    def receive_packet(self, packet: Packet):
        self.process_packet(packet)

    def process_packet(self, packet: Packet | None = None):
        try:
            result = self.function.execute()
            is_stop = result is None or isinstance(result, StopSignal)
            if is_stop:
                stop_signal = result if isinstance(result, StopSignal) else StopSignal(self.name)
                self.router.send_stop_signal(stop_signal)
                self.ctx.send_stop_signal_back(self.name)
                self.ctx.set_stop_signal()
                return
            success = self.router.send(Packet(result))
            if not success:
                self.ctx.set_stop_signal()
        except Exception as exc:
            self.logger.error(f"Error in {self.name}.process(): {exc}", exc_info=True)


class KeyByOperator(BaseOperator):
    def __init__(self, *args, partition_strategy: str = "hash", **kwargs):
        super().__init__(*args, **kwargs)
        self.partition_strategy = partition_strategy

    def process_packet(self, packet: Packet | None = None):
        try:
            if packet is None or packet.payload is None:
                return
            extracted_key = self.process(packet.payload)
            keyed_packet = packet.update_key(extracted_key, self.partition_strategy)
            self.router.send(keyed_packet)
        except Exception as exc:
            self.logger.error(f"Error in KeyByOperator {self.name}: {exc}", exc_info=True)
            if packet:
                self.router.send(packet)

    def process(self, raw_data: Any, input_index: int = 0) -> Any:
        try:
            return self.function.execute(raw_data)
        except Exception as exc:
            self.logger.error(f"Error extracting key in {self.name}: {exc}", exc_info=True)
            return raw_data


class FutureOperator(BaseOperator):
    def __init__(self, function_factory: FunctionFactory, ctx, env_name: str = ""):
        super().__init__(function_factory, ctx)
        self.is_future = True
        self.basename = getattr(ctx, "name", env_name)

    def process(self, data: Any) -> Any:
        raise RuntimeError("FutureOperator should not be called directly. It's a placeholder.")

    def emit(self, result: Any) -> None:
        raise RuntimeError("FutureOperator should not be called directly. It's a placeholder.")

    def process_packet(self, packet: Packet | None = None):
        raise RuntimeError("FutureOperator should not receive packets directly.")


class JoinOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validate_function()
        self._validated = True
        self.processed_count = 0
        self.emitted_count = 0
        self.received_stop_signals = set()

    def _validate_function(self) -> None:
        if not hasattr(self.function, "is_join") or not self.function.is_join:  # type: ignore[attr-defined]
            raise TypeError(
                f"{self.__class__.__name__} requires Join function with is_join=True, got {type(self.function).__name__}"
            )
        if not hasattr(self.function, "execute"):
            raise TypeError(
                f"Join function {type(self.function).__name__} must implement execute method"
            )
        if getattr(self.function.execute, "__isabstractmethod__", False):
            raise TypeError(
                f"Join function {type(self.function).__name__} must implement execute method (currently abstract)"
            )

    def process_packet(self, packet: Packet | None = None):
        try:
            if packet is None or packet.payload is None:
                return
            if not packet.is_keyed():
                self.logger.warning(
                    f"JoinOperator '{self.name}' received non-keyed packet, skipping."
                )
                return
            payload = packet.payload
            join_key = packet.partition_key
            stream_tag = packet.input_index
            if payload is None:
                return
            self.processed_count += 1
            join_results = self.function.execute(payload, join_key, stream_tag)
            if join_results is not None:
                if not isinstance(join_results, list):
                    join_results = [join_results] if join_results is not None else []
                for result in join_results:
                    if result is not None:
                        self._emit_join_result(result, join_key, packet)
                        self.emitted_count += 1
        except Exception as exc:
            self.logger.error(f"Error in JoinOperator '{self.name}': {exc}", exc_info=True)

    def handle_stop_signal(
        self,
        stop_signal_name: str | None = None,
        input_index: int | None = None,
        signal: Any = None,
    ):
        try:
            if signal is not None:
                signal_name = signal.name if isinstance(signal, StopSignal) else str(signal)
            elif stop_signal_name is not None:
                signal_name = stop_signal_name
            else:
                return
            self.received_stop_signals.add(signal_name)
            source_signals = {
                sig.name if isinstance(sig, StopSignal) else sig
                for sig in self.received_stop_signals
                if ("Source" in (sig.name if isinstance(sig, StopSignal) else str(sig)))
            }
            expected_sources = 2
            if len(source_signals) >= expected_sources:
                self.ctx.send_stop_signal_back(self.name)
                self.router.send_stop_signal(StopSignal(self.name))
                self.ctx.set_stop_signal()
        except Exception as exc:
            self.logger.error(
                f"Error in JoinOperator '{self.name}' handle_stop_signal: {exc}",
                exc_info=True,
            )

    def _emit_join_result(self, result_data: Any, join_key: Any, original_packet: Packet):
        try:
            result_packet = Packet(
                payload=result_data,
                input_index=0,
                partition_key=join_key,
                partition_strategy=original_packet.partition_strategy or "hash",
            )
            self.router.send(result_packet)
        except Exception as exc:
            self.logger.error(
                f"Failed to emit join result for key '{join_key}': {exc}", exc_info=True
            )


class CoMapOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validate_function()
        self._validated = True
        self.received_stop_signals = set()
        self.expected_input_count = None

    def _validate_function(self) -> None:
        if not hasattr(self.function, "is_comap") or not self.function.is_comap:  # type: ignore[attr-defined]
            raise TypeError(
                f"{self.__class__.__name__} requires CoMap function with is_comap=True, got {type(self.function).__name__}"
            )
        for method_name in ["map0", "map1"]:
            if not hasattr(self.function, method_name):
                raise TypeError(
                    f"CoMap function {type(self.function).__name__} must implement {method_name} method"
                )

    def process_packet(self, packet: Packet | None = None):
        try:
            if packet is None or packet.payload is None:
                return
            map_method = getattr(self.function, f"map{packet.input_index}")
            result = map_method(packet.payload)
            if result is not None:
                self.router.send(packet.inherit_partition_info(result))
        except Exception as exc:
            self.logger.error(f"Error in CoMapOperator {self.name}: {exc}", exc_info=True)
            error_result = {
                "type": "comap_error",
                "error": str(exc),
                "original_payload": packet.payload if packet else None,
                "input_index": packet.input_index if packet else -1,
                "operator": self.name,
            }
            try:
                if packet:
                    self.router.send(packet.inherit_partition_info(error_result))
            except Exception as send_error:
                self.logger.error(
                    f"Failed to send error result in CoMapOperator {self.name}: {send_error}"
                )

    def handle_stop_signal(
        self, stop_signal_name: str | None = None, input_index: int | None = None
    ):
        try:
            if input_index is not None:
                self.received_stop_signals.add(input_index)
            if self.expected_input_count is None:
                count = 0
                while hasattr(self.function, f"map{count}") and not getattr(
                    getattr(self.function, f"map{count}"), "__isabstractmethod__", False
                ):
                    count += 1
                self.expected_input_count = count or getattr(self.router, "input_count", 2)
            if len(self.received_stop_signals) >= self.expected_input_count:
                self.router.send_stop_signal(StopSignal(self.name, source=self.name))
                self.ctx.set_stop_signal()
        except Exception as exc:
            self.logger.error(
                f"Error in CoMapOperator '{self.name}' handle_stop_signal: {exc}",
                exc_info=True,
            )
