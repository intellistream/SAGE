from sage.kernel.runtime.communication.packet import Packet

from .base_operator import BaseOperator


class CoMapOperator(BaseOperator):
    """
    CoMap操作符 - 处理多输入流的分别处理操作

    CoMapOperator专门用于处理CoMap函数，它会根据输入的input_index
    直接路由到相应的mapN方法，而不是使用统一的execute方法。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 验证函数类型（在运行时初始化后进行）
        self._validate_function()
        self._validated = True

        # 跟踪接收到的停止信号
        self.received_stop_signals = set()  # 记录哪些stream已经发送了停止信号

        # 记录输入流的数量，用于判断是否所有流都已停止
        self.expected_input_count = None

    def _validate_function(self) -> None:
        """
        验证函数是否为CoMap函数

        Raises:
            TypeError: 如果函数不是CoMap函数
        """
        if not hasattr(self.function, "is_comap") or not self.function.is_comap:  # type: ignore[attr-defined]
            raise TypeError(
                f"{self.__class__.__name__} requires CoMap function with is_comap=True, "
                f"got {type(self.function).__name__}"
            )

        # 验证必需的map0和map1方法
        required_methods = ["map0", "map1"]
        for method_name in required_methods:
            if not hasattr(self.function, method_name):
                raise TypeError(
                    f"CoMap function {type(self.function).__name__} must implement {method_name} method"
                )

        self.logger.debug(f"Validated CoMap function {type(self.function).__name__}")

    def process_packet(self, packet: "Packet | None" = None):
        """CoMap处理多输入，保持分区信息"""
        try:
            if packet is None or packet.payload is None:
                return

            # 根据输入索引调用对应的mapN方法
            input_index = packet.input_index
            map_method = getattr(self.function, f"map{input_index}")
            result = map_method(packet.payload)

            if result is not None:
                # 继承原packet的分区信息
                result_packet = packet.inherit_partition_info(result)
                self.router.send(result_packet)

        except Exception as e:
            self.logger.error(f"Error in CoMapOperator {self.name}: {e}", exc_info=True)

            # 发送错误结果，确保下游仍能收到数据（关键修复）
            error_result = {
                "type": "comap_error",
                "error": str(e),
                "original_payload": packet.payload if packet else None,
                "input_index": packet.input_index if packet else -1,
                "operator": self.name,
            }

            try:
                if packet:
                    error_packet = packet.inherit_partition_info(error_result)
                    self.router.send(error_packet)
                    self.logger.info(f"CoMapOperator {self.name}: Sent error result downstream")
            except Exception as send_error:
                self.logger.error(
                    f"Failed to send error result in CoMapOperator {self.name}: {send_error}"
                )

    def handle_stop_signal(
        self, stop_signal_name: str | None = None, input_index: int | None = None
    ):
        """
        处理停止信号的传播

        CoMap操作需要特殊处理停止信号：
        - 记录哪个stream发送了停止信号
        - 只有当所有输入流都停止时，才向下游传播停止信号（修复关键bug）
        """
        try:
            if input_index is not None:
                self.received_stop_signals.add(input_index)
                self.logger.info(
                    f"CoMapOperator '{self.name}' received stop signal from stream {input_index}"
                )

            # 如果还没有初始化期望的输入流数量，尝试从函数获取
            if self.expected_input_count is None:
                try:
                    # 通过检查函数的mapN方法数量来确定预期的输入数量
                    count = 0
                    method_index = 0
                    while True:
                        method_name = f"map{method_index}"
                        if hasattr(self.function, method_name):
                            method = getattr(self.function, method_name)
                            # 检查方法是否实际可调用（不是抽象方法）
                            if callable(method) and not getattr(
                                method, "__isabstractmethod__", False
                            ):
                                count += 1
                                method_index += 1
                            else:
                                break
                        else:
                            break

                    # 如果通过函数找到了mapN方法，使用该数量
                    if count > 0:
                        self.expected_input_count = count
                    else:
                        # 从路由器的入站连接数推断（备用方案）
                        self.expected_input_count = getattr(self.router, "input_count", 2)

                    self.logger.debug(
                        f"CoMapOperator '{self.name}' expecting {self.expected_input_count} input streams"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"CoMapOperator '{self.name}' failed to determine input count: {e}, defaulting to 2"
                    )
                    self.expected_input_count = 2

            # 修复关键bug：只有当所有输入流都停止时，才向下游传播停止信号
            if len(self.received_stop_signals) >= self.expected_input_count:
                self.logger.info(
                    f"CoMapOperator '{self.name}' received stop signals from all {self.expected_input_count} input streams, "
                    f"propagating stop signal downstream"
                )

                # 向下游传播停止信号
                from sage.kernel.runtime.communication.packet import StopSignal

                stop_signal = StopSignal(self.name, source=self.name)
                self.router.send_stop_signal(stop_signal)

                # 通知context停止
                self.ctx.set_stop_signal()
            else:
                self.logger.debug(
                    f"CoMapOperator '{self.name}' waiting for more stop signals: "
                    f"received {len(self.received_stop_signals)}/{self.expected_input_count}"
                )

        except Exception as e:
            self.logger.error(
                f"Error in CoMapOperator '{self.name}' handle_stop_signal: {e}",
                exc_info=True,
            )

    def _get_max_supported_index(self) -> int:
        """
        获取支持的最大输入流索引

        Returns:
            int: 最大支持的输入流索引
        """
        max_index = -1
        index = 0

        # 检查有多少个mapN方法被实现
        while True:
            method_name = f"map{index}"
            if hasattr(self.function, method_name):
                try:
                    # 尝试调用方法看是否抛出NotImplementedError
                    method = getattr(self.function, method_name)
                    # 检查方法是否为抽象方法或抛出NotImplementedError
                    if not getattr(method, "__isabstractmethod__", False):
                        max_index = index
                except Exception:
                    # 如果获取方法时出错，停止检查
                    break
                index += 1
            else:
                break

        return max_index

    def get_supported_input_methods(self) -> list[str]:
        """
        获取所有支持的mapN方法列表

        Returns:
            list[str]: 支持的方法名列表
        """
        methods = []
        index = 0

        while True:
            method_name = f"map{index}"
            if hasattr(self.function, method_name):
                method = getattr(self.function, method_name)
                if not getattr(method, "__isabstractmethod__", False):
                    methods.append(method_name)
                index += 1
            else:
                break

        return methods

    def __repr__(self) -> str:
        if hasattr(self, "function") and self.function:
            function_name = self.function.__class__.__name__
            if self._validated:
                max_index = self._get_max_supported_index()
                return f"<{self.__class__.__name__} {function_name} supports:0-{max_index}>"
            else:
                return f"<{self.__class__.__name__} {function_name} (not validated)>"
        else:
            return f"<{self.__class__.__name__} (no function)>"
