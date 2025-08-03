"""
Queue Creation Strategy - 队列创建策略

根据运行环境和需求智能选择最合适的队列类型
"""

from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sage.runtime.communication.queue.base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)


class QueueCreationStrategy:
    """队列创建策略"""
    
    @staticmethod
    def create_task_input_queue(task_name: str, is_remote: bool, **kwargs) -> 'BaseQueueDescriptor':
        """为任务创建输入队列"""
        queue_id = f"input_{task_name}"
        
        if is_remote:
            # 远程环境优先使用Ray队列
            try:
                from sage.runtime.communication.queue.ray_queue_descriptor import RayQueueDescriptor
                return RayQueueDescriptor(queue_id=queue_id, **kwargs)
            except ImportError:
                logger.warning("Ray not available, falling back to local queue")
                from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
                return PythonQueueDescriptor(queue_id=queue_id, **kwargs)
        else:
            # 本地环境优先使用SAGE队列，退化到本地队列
            try:
                from sage.runtime.communication.queue.sage_queue_descriptor import SageQueueDescriptor
                return SageQueueDescriptor(queue_id=queue_id, **kwargs)
            except Exception as e:
                logger.debug(f"SAGE queue not available ({e}), using Python queue")
                from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
                return PythonQueueDescriptor(queue_id=queue_id, **kwargs)
    
    @staticmethod
    def create_inter_task_queue(source_task: str, target_task: str, is_remote: bool, **kwargs) -> 'BaseQueueDescriptor':
        """为任务间通信创建队列"""
        queue_id = f"{source_task}_to_{target_task}"
        
        if is_remote:
            try:
                from sage.runtime.communication.queue.ray_queue_descriptor import RayQueueDescriptor
                return RayQueueDescriptor(queue_id=queue_id, **kwargs)
            except ImportError:
                logger.warning("Ray not available, falling back to local queue")
                from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
                return PythonQueueDescriptor(queue_id=queue_id, **kwargs)
        else:
            try:
                from sage.runtime.communication.queue.sage_queue_descriptor import SageQueueDescriptor
                return SageQueueDescriptor(queue_id=queue_id, **kwargs)
            except Exception as e:
                logger.debug(f"SAGE queue not available ({e}), using Python queue")
                from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
                return PythonQueueDescriptor(queue_id=queue_id, **kwargs)
    
    @staticmethod
    def create_service_request_queue(service_name: str, is_remote: bool, **kwargs) -> 'BaseQueueDescriptor':
        """为服务创建请求队列"""
        queue_id = f"service_request_{service_name}"
        
        if is_remote:
            try:
                from sage.runtime.communication.queue.ray_queue_descriptor import RayQueueDescriptor
                return RayQueueDescriptor(queue_id=queue_id, **kwargs)
            except ImportError:
                logger.warning("Ray not available, falling back to local queue")
                from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
                return PythonQueueDescriptor(queue_id=queue_id, **kwargs)
        else:
            try:
                from sage.runtime.communication.queue.sage_queue_descriptor import SageQueueDescriptor
                return SageQueueDescriptor(queue_id=queue_id, **kwargs)
            except Exception as e:
                logger.debug(f"SAGE queue not available ({e}), using Python queue")
                from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
                return PythonQueueDescriptor(queue_id=queue_id, **kwargs)
    
    @staticmethod
    def create_service_response_queue(service_name: str, node_name: str, is_remote: bool, **kwargs) -> 'BaseQueueDescriptor':
        """为服务响应创建队列"""
        queue_id = f"service_response_{service_name}_{node_name}"
        
        if is_remote:
            try:
                from sage.runtime.communication.queue.ray_queue_descriptor import RayQueueDescriptor
                return RayQueueDescriptor(queue_id=queue_id, **kwargs)
            except ImportError:
                logger.warning("Ray not available, falling back to local queue")
                from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
                return PythonQueueDescriptor(queue_id=queue_id, **kwargs)
        else:
            try:
                from sage.runtime.communication.queue.sage_queue_descriptor import SageQueueDescriptor
                return SageQueueDescriptor(queue_id=queue_id, **kwargs)
            except Exception as e:
                logger.debug(f"SAGE queue not available ({e}), using Python queue")
                from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
                return PythonQueueDescriptor(queue_id=queue_id, **kwargs)
    
    @staticmethod
    def get_default_queue_params(is_remote: bool) -> dict:
        """获取默认队列参数"""
        if is_remote:
            return {
                'maxsize': 1000,
            }
        else:
            return {
                'maxsize': 1024 * 1024,  # SAGE队列使用字节大小
                'auto_cleanup': True,
                'enable_multi_tenant': True
            }
