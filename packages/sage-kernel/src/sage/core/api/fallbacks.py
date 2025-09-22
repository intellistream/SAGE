"""
回退实现：当闭源模块不可用时的开源替代实现
这些是基础的模拟实现，提供基本功能但不包含企业级特性
"""

import logging
from typing import Any, Dict, List, Optional
import warnings

class MockJobManagerClient:
    """JobManagerClient 的开源模拟实现"""
    
    def __init__(self, *args, **kwargs):
        self._logger = logging.getLogger(__name__)
        self._logger.warning("使用 JobManagerClient 的开源模拟实现，企业级功能不可用")
    
    def submit_job(self, job_config: Dict[str, Any]) -> str:
        """模拟提交作业"""
        job_id = f"mock_job_{id(job_config)}"
        self._logger.info(f"模拟作业提交: {job_id}")
        return job_id
    
    def get_job_status(self, job_id: str) -> str:
        """模拟获取作业状态"""
        return "COMPLETED"
    
    def cancel_job(self, job_id: str) -> bool:
        """模拟取消作业"""
        self._logger.info(f"模拟取消作业: {job_id}")
        return True
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """模拟列出作业"""
        return []

class MockCustomLogger:
    """CustomLogger 的开源模拟实现"""
    
    def __init__(self, name: str = "sage", level: str = "INFO"):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # 如果没有处理器，添加一个控制台处理器
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._logger.debug(message)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._logger.info(message)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._logger.warning(message)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self._logger.error(message)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._logger.critical(message)

class MockMiddlewareManager:
    """MiddlewareManager 的开源模拟实现"""
    
    def __init__(self):
        self._middlewares = []
        self._logger = logging.getLogger(__name__)
        self._logger.warning("使用 MiddlewareManager 的开源模拟实现")
    
    def register_middleware(self, middleware: Any):
        """注册中间件"""
        self._middlewares.append(middleware)
        self._logger.info(f"注册中间件: {type(middleware).__name__}")
    
    def process_request(self, request: Any) -> Any:
        """处理请求"""
        # 简单的直通处理
        return request
    
    def process_response(self, response: Any) -> Any:
        """处理响应"""
        # 简单的直通处理
        return response

class MockOpenAIClient:
    """OpenAIClient 的开源模拟实现"""
    
    def __init__(self, api_key: Optional[str] = None):
        self._logger = logging.getLogger(__name__)
        self._logger.warning("使用 OpenAIClient 的开源模拟实现，不会调用真实API")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """模拟聊天完成"""
        return "这是模拟的AI响应。请配置真实的OpenAI API密钥以获得实际功能。"
    
    def embedding(self, text: str, **kwargs) -> List[float]:
        """模拟文本嵌入"""
        # 返回随机嵌入向量
        import random
        return [random.random() for _ in range(768)]

class MockTaskContext:
    """TaskContext 的开源模拟实现"""
    
    def __init__(self, task_id: str = "mock_task"):
        self.task_id = task_id
        self._logger = logging.getLogger(__name__)
    
    def get_task_id(self) -> str:
        return self.task_id
    
    def get_parallelism(self) -> int:
        return 1
    
    def set_parallelism(self, parallelism: int):
        pass

class MockServiceContext:
    """ServiceContext 的开源模拟实现"""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
    def get_service_name(self) -> str:
        return "mock_service"
    
    def get_configuration(self) -> Dict[str, Any]:
        return {}

# 模拟 dill 序列化模块
class MockDill:
    """dill 序列化的模拟实现"""
    
    @staticmethod
    def serialize_object(obj: Any) -> bytes:
        """模拟对象序列化"""
        import pickle
        return pickle.dumps(obj)
    
    @staticmethod
    def deserialize_object(data: bytes) -> Any:
        """模拟对象反序列化"""
        import pickle
        return pickle.loads(data)
    
    @staticmethod
    def trim_object_for_ray(obj: Any) -> Any:
        """模拟为 Ray 修剪对象"""
        return obj

# 创建模拟 dill 模块实例
mock_dill = MockDill()

def serialize_object(obj: Any) -> bytes:
    """序列化对象的兼容性函数"""
    return mock_dill.serialize_object(obj)

def deserialize_object(data: bytes) -> Any:
    """反序列化对象的兼容性函数"""
    return mock_dill.deserialize_object(data)

def trim_object_for_ray(obj: Any) -> Any:
    """为 Ray 修剪对象的兼容性函数"""
    return mock_dill.trim_object_for_ray(obj)

# 警告用户正在使用模拟实现
def _warn_mock_usage(class_name: str):
    """警告用户正在使用模拟实现"""
    warnings.warn(
        f"正在使用 {class_name} 的开源模拟实现。"
        f"某些企业级功能可能不可用或行为有所不同。"
        f"要获得完整功能，请确保正确安装闭源依赖包。",
        UserWarning,
        stacklevel=3
    )
