import json
import os
import time
from typing import TYPE_CHECKING

from sage.kernel.api.operator.base_operator import BaseOperator
from sage.kernel.runtime.communication.packet import Packet
from sage.kernel.runtime.context.task_context import TaskContext

if TYPE_CHECKING:
    from sage.kernel.runtime.factory.function_factory import FunctionFactory


class MapOperator(BaseOperator):
    def __init__(
        self,
        function_factory: "FunctionFactory",
        ctx: "TaskContext",
        enable_profile=False,
        *args,
        **kwargs,
    ):
        # 从 kwargs 中移除 enable_profile，避免传递给 BaseOperator
        kwargs.pop("enable_profile", None)
        super().__init__(function_factory, ctx, *args, **kwargs)
        self.enable_profile = enable_profile
        if self.enable_profile:
            self._setup_time_tracking()

    def _setup_time_tracking(self):
        """设置时间统计的存储路径"""
        if hasattr(self.ctx, "env_base_dir") and self.ctx.env_base_dir:
            self.time_base_path = os.path.join(
                self.ctx.env_base_dir, ".sage_states", "time_records"
            )
        else:
            # 使用默认路径
            self.time_base_path = os.path.join(os.getcwd(), ".sage_states", "time_records")

        os.makedirs(self.time_base_path, exist_ok=True)
        self.time_records = []

    def _save_time_record(self, duration: float):
        """保存时间记录"""
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "duration": duration,
            "function_name": self.function.__class__.__name__,
            "operator_name": self.name,
        }
        self.time_records.append(record)
        self._persist_time_records()

    def _persist_time_records(self):
        """将时间记录持久化到文件"""
        if not self.enable_profile or not self.time_records:
            return

        timestamp = int(time.time())
        filename = f"time_records_{timestamp}.json"
        path = os.path.join(self.time_base_path, filename)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.time_records, f, ensure_ascii=False, indent=2)
            self.time_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist time records: {e}")

    def process_packet(self, packet: "Packet | None" = None):
        try:
            if packet is None or packet.payload is None:
                self.logger.warning(f"Operator {self.name} received empty data")
            else:
                # 执行前记录时间
                start_time = time.time()

                # 执行function
                result = self.function.execute(packet.payload)

                # 执行后记录时间
                end_time = time.time()
                duration = end_time - start_time

                # 将时间信息添加到结果中（如果结果是字典）
                if isinstance(result, dict):
                    # 根据 function 类型添加对应的时间字段
                    function_class_name = self.function.__class__.__name__
                    
                    # Retriever 类
                    if 'Retriever' in function_class_name:
                        result['retrieval_time'] = duration
                    # Reranker 类
                    elif 'Reranker' in function_class_name:
                        result['reranking_time'] = duration
                    # Refiner 类
                    elif 'Refiner' in function_class_name:
                        result['refining_time'] = duration
                    # Generator 类
                    elif 'Generator' in function_class_name:
                        result['generation_time'] = duration
                    # Promptor 类（通常不需要时间字段，因为很快）
                    # 其他情况可以添加通用的 execution_time
                    else:
                        result['execution_time'] = duration

                # 保存时间记录到文件（只有enable_profile=True时才保存）
                if self.enable_profile:
                    self._save_time_record(duration)

                self.logger.debug(
                    f"Operator {self.name} processed data in {duration:.4f}s with result: {result}"
                )
                result_packet = (
                    packet.inherit_partition_info(result) if (result is not None) else None
                )
                if result_packet is not None:
                    self.router.send(result_packet)  # type: ignore

        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_time_records()
            except Exception:
                pass
