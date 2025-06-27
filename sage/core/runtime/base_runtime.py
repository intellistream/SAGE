from abc import ABC, abstractmethod

class BaseRuntime(ABC):
    """执行后端抽象接口"""
    
    # @abstractmethod
    # def submit_task(self, task) -> str:
    #     """提交任务执行，返回任务句柄"""
    #     pass
    
    # @abstractmethod
    # def stop_task(self, task_handle: str):
    #     """停止指定任务"""
    #     pass
    
    # @abstractmethod
    # def get_status(self, task_handle: str):
    #     """获取任务状态"""
    #     pass

