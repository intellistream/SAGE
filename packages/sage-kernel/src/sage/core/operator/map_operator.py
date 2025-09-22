
from sage.kernel import TaskContext
from .base_operator import BaseOperator
from sage.core.api.function.map_function import MapFunction
import time
import os
import json
from typing import Union, Any, TYPE_CHECKING
from sage.core.communication.packet import Packet
if TYPE_CHECKING:
    from sage.core.factory.function_factory import FunctionFactory

class MapOperator(BaseOperator):
    def __init__(self, function_factory: 'FunctionFactory', ctx: 'TaskContext', enable_profile=False, *args, **kwargs):
        # 从 kwargs 中移除 enable_profile，避免传递给 BaseOperator
        kwargs.pop('enable_profile', None)
        super().__init__(function_factory, ctx, *args, **kwargs)
        self.enable_profile = enable_profile
        if self.enable_profile:
            self._setup_time_tracking()

    def _setup_time_tracking(self):
        """设置时间统计的存储路径"""
        if hasattr(self.ctx, 'env_base_dir') and self.ctx.env_base_dir:
            self.time_base_path = os.path.join(self.ctx.env_base_dir, ".sage_states", "time_records")
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
            'timestamp': time.time(),
            'duration': duration,
            'function_name': self.function.__class__.__name__,
            'operator_name': self.name
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
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.time_records, f, ensure_ascii=False, indent=2)
            self.time_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist time records: {e}")

    def process_packet(self, packet: 'Packet' = None):
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

                # 保存时间记录（只有enable_profile=True时才保存）
                if self.enable_profile:
                    self._save_time_record(duration)

                self.logger.debug(f"Operator {self.name} processed data with result: {result}")
                result_packet = packet.inherit_partition_info(result) if (result is not None) else None
                if result_packet is not None:
                    self.router.send(result_packet)

        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, 'enable_profile') and self.enable_profile:
            try:
                self._persist_time_records()
            except:
                pass
