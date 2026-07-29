from typing import Any

from sage.kernel.runtime.communication.packet import Packet

from .base_operator import BaseOperator


class JoinOperator(BaseOperator):
    """
    Join操作符 - 处理多输入流的关联操作

    JoinOperator专门用于处理Join函数，它会提取packet的payload、key和tag信息，
    然后调用join function的execute方法进行关联处理。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 验证函数类型（在运行时初始化后进行）
        self._validate_function()
        self._validated = True

        # 统计信息
        self.processed_count = 0
        self.emitted_count = 0

        # 跟踪接收到的停止信号
        self.received_stop_signals = set()  # 记录哪些stream已经发送了停止信号

    def _validate_function(self) -> None:
        """
        验证函数是否为Join函数

        Raises:
            TypeError: 如果函数不是Join函数
        """
        # JoinFunction has is_join attribute, BaseFunction doesn't
        # hasattr check ensures runtime safety
        if not hasattr(self.function, "is_join") or not self.function.is_join:  # type: ignore[attr-defined]
            raise TypeError(
                f"{self.__class__.__name__} requires Join function with is_join=True, "
                f"got {type(self.function).__name__}"
            )

        # 验证必需的execute方法
        if not hasattr(self.function, "execute"):
            raise TypeError(
                f"Join function {type(self.function).__name__} must implement execute method"
            )

        # 验证execute方法不是抽象方法
        execute_method = self.function.execute
        if getattr(execute_method, "__isabstractmethod__", False):
            raise TypeError(
                f"Join function {type(self.function).__name__} must implement execute method "
                f"(currently abstract)"
            )

        self.logger.debug(f"Validated Join function {type(self.function).__name__}")

    def process_packet(self, packet: "Packet | None" = None):
        """Join处理，将packet信息传递给join function"""
        try:
            if packet is None or packet.payload is None:
                self.logger.debug("Received empty packet, skipping")
                return

            # 必须是keyed packet
            if not packet.is_keyed():
                self.logger.warning(
                    f"JoinOperator '{self.name}' received non-keyed packet, skipping. "
                    f"Join operations require keyed streams."
                )
                return

            # 提取必要信息
            payload = packet.payload
            join_key = packet.partition_key
            stream_tag = packet.input_index

            # 过滤None payload（这可能是因为BatchFunction返回None导致的）
            if payload is None:
                self.logger.debug(
                    f"JoinOperator '{self.name}' received None payload from stream {stream_tag}, skipping"
                )
                return

            self.processed_count += 1

            self.logger.debug(
                f"JoinOperator '{self.name}' processing: "
                f"key='{join_key}', tag={stream_tag}, payload_type={type(payload).__name__}"
            )

            # 调用join function的execute方法
            join_results = self.function.execute(payload, join_key, stream_tag)

            # 处理返回结果
            if join_results is not None:
                # 如果返回的不是列表，转换为列表
                if not isinstance(join_results, list):
                    join_results = [join_results] if join_results is not None else []

                # 发送所有结果
                for result in join_results:
                    if result is not None:
                        self._emit_join_result(result, join_key, packet)
                        self.emitted_count += 1

            # 定期打印统计信息
            if self.processed_count % 100 == 0:
                self.logger.info(
                    f"JoinOperator '{self.name}' stats: "
                    f"processed={self.processed_count}, emitted={self.emitted_count}, "
                    f"ratio={self.emitted_count / max(1, self.processed_count):.2f}"
                )

        except Exception as e:
            self.logger.error(f"Error in JoinOperator '{self.name}': {e}", exc_info=True)
            # 不重新抛出异常，避免中断整个流处理

    def handle_stop_signal(
        self,
        stop_signal_name: str | None = None,
        input_index: int | None = None,
        signal: Any = None,
    ):
        """
        处理停止信号的传播

        Join操作需要特殊处理停止信号：
        - 记录哪个stream发送了停止信号
        - 当所有输入流都停止时，才向下游传播停止信号
        """
        try:
            # 处理来自不同调用方式的参数
            if signal is not None:
                # 来自 task_context 的调用，signal 是 StopSignal 对象
                from sage.kernel.runtime.communication.packet import StopSignal

                if isinstance(signal, StopSignal):
                    signal_name = signal.name
                else:
                    signal_name = str(signal)
            elif stop_signal_name is not None:
                # 来自 base_task 的调用，使用传统参数
                signal_name = stop_signal_name
            else:
                self.logger.warning(f"JoinOperator '{self.name}' received stop signal with no name")
                return

            # 记录收到的停止信号，使用信号名称作为唯一标识
            self.received_stop_signals.add(signal_name)
            self.logger.info(
                f"JoinOperator '{self.name}' received stop signal from '{signal_name}', "
                f"total received: {len(self.received_stop_signals)} "
                f"(all signals: {list(self.received_stop_signals)})"
            )

            # 检查是否所有输入流都已停止
            # 对于 Join 操作符，我们需要等待来自不同源节点的停止信号
            # 在当前的拓扑中，两个源可能通过同一个KeyBy节点连接到Join
            # 所以我们需要特殊处理这种情况

            # 检查是否收到了所有原始源的停止信号
            # 这些应该是以 "Source" 开头的节点，或者包含 "Source" 的节点
            source_signals = set()
            for sig in self.received_stop_signals:
                if isinstance(sig, str):
                    # String signal name - 检查是否包含 "Source" 或者以 "Source" 开头
                    if "Source" in sig or sig.startswith("Source"):
                        source_signals.add(sig)
                else:
                    # StopSignal object
                    from sage.kernel.runtime.communication.packet import (
                        StopSignal,
                    )

                    if isinstance(sig, StopSignal) and (
                        "Source" in sig.name or sig.name.startswith("Source")
                    ):
                        source_signals.add(sig.name)

            # 对于双流Join，固定期望2个源的停止信号
            # 这里不使用动态判断，避免循环依赖问题
            expected_sources = 2  # Join操作固定期望2个源

            self.logger.info(
                f"JoinOperator '{self.name}' stop signal status: "
                f"{len(source_signals)}/{expected_sources} source signals "
                f"(source signals: {list(source_signals)}, all signals: {list(self.received_stop_signals)})"
            )

            if len(source_signals) >= expected_sources:
                self.logger.info(
                    f"JoinOperator '{self.name}' all {expected_sources} source streams stopped, "
                    f"propagating stop signal downstream"
                )

                # 所有源流都停止了，先通知JobManager该节点完成
                self.logger.info(f"JoinOperator '{self.name}' notifying JobManager of completion")
                self.ctx.send_stop_signal_back(self.name)

                # 然后向下游传播停止信号
                from sage.kernel.runtime.communication.packet import StopSignal

                stop_signal = StopSignal(self.name)
                self.logger.info(f"JoinOperator '{self.name}' sending stop signal to downstream")
                self.router.send_stop_signal(stop_signal)

                # 通知context停止
                self.logger.info(f"JoinOperator '{self.name}' setting context stop signal")
                self.ctx.set_stop_signal()
            else:
                self.logger.info(
                    f"JoinOperator '{self.name}' waiting for more source streams to stop: "
                    f"{len(source_signals)}/{expected_sources} "
                    f"(source signals received: {list(source_signals)})"
                )

                # 重要：不要向下游传播停止信号，也不要停止context
                # 只是记录收到的停止信号，继续等待其他源流

        except Exception as e:
            self.logger.error(
                f"Error in JoinOperator '{self.name}' handle_stop_signal: {e}",
                exc_info=True,
            )

    def _emit_join_result(self, result_data: Any, join_key: Any, original_packet: "Packet"):
        """
        发送join结果，保持分区信息

        Args:
            result_data: join function返回的结果数据
            join_key: 关联键
            original_packet: 原始packet，用于继承其他信息
        """
        try:
            # 创建结果packet，保持分区信息
            result_packet = Packet(
                payload=result_data,
                input_index=0,  # Join的输出默认为0
                partition_key=join_key,
                partition_strategy=original_packet.partition_strategy or "hash",
            )

            self.router.send(result_packet)

            self.logger.debug(
                f"JoinOperator '{self.name}' emitted result for key '{join_key}': "
                f"{type(result_data).__name__}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to emit join result for key '{join_key}': {e}", exc_info=True
            )

    def get_statistics(self) -> dict:
        """
        获取Join操作统计信息

        Returns:
            dict: 统计信息字典
        """
        return {
            "operator_name": self.name,
            "function_type": type(self.function).__name__,
            "processed_packets": self.processed_count,
            "emitted_results": self.emitted_count,
            "join_ratio": self.emitted_count / max(1, self.processed_count),
            "is_validated": self._validated,
        }

    def debug_print_statistics(self):
        """打印详细的统计信息"""
        stats = self.get_statistics()
        print(f"\n📊 JoinOperator '{self.name}' Statistics:")
        print(f"   Function: {stats['function_type']}")
        print(f"   Processed packets: {stats['processed_packets']}")
        print(f"   Emitted results: {stats['emitted_results']}")
        print(f"   Join ratio: {stats['join_ratio']:.2%}")
        print(f"   Validated: {stats['is_validated']}")

    def _validate_execute_method_signature(self) -> bool:
        """
        验证execute方法的签名是否正确

        Returns:
            bool: 签名是否正确
        """
        import inspect

        try:
            execute_method = self.function.execute
            signature = inspect.signature(execute_method)
            params = list(signature.parameters.keys())

            # 期望的参数：self, payload, key, tag (至少)
            expected_min_params = ["self", "payload", "key", "tag"]

            if len(params) < len(expected_min_params):
                self.logger.warning(
                    f"Join function execute method has insufficient parameters. "
                    f"Expected: {expected_min_params[1:]}, Got: {params[1:]}"
                )
                return False

            # 检查前几个参数名
            for i, expected_param in enumerate(expected_min_params):
                if i < len(params) and params[i] != expected_param:
                    self.logger.warning(
                        f"Join function execute method parameter {i} "
                        f"expected '{expected_param}', got '{params[i]}'"
                    )

            return True

        except Exception as e:
            self.logger.warning(f"Could not validate execute method signature: {e}")
            return False

    def get_supported_stream_count(self) -> int:
        """
        获取支持的输入流数量

        目前Join操作支持2个输入流

        Returns:
            int: 支持的输入流数量
        """
        return 2  # 目前固定为2流join

    def __repr__(self) -> str:
        if hasattr(self, "function") and self.function:
            function_name = self.function.__class__.__name__
            if self._validated:
                stream_count = self.get_supported_stream_count()
                join_type = getattr(self.function, "join_type", "custom")
                return (
                    f"<{self.__class__.__name__} {function_name} "
                    f"type:{join_type} streams:{stream_count} "
                    f"processed:{self.processed_count} emitted:{self.emitted_count}>"
                )
            else:
                return f"<{self.__class__.__name__} {function_name} (not validated)>"
        else:
            return f"<{self.__class__.__name__} (no function)>"
