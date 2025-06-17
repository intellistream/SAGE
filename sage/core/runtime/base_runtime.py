import logging
from abc import ABC, abstractmethod
import ray
from typing import Dict, List, Optional, Any

from sage.core.dag.dag import DAG
from sage.core.dag.dag_manager import DAGManager
from sage.core.dag.dag_node import BaseDAGNode, ContinuousDAGNode, OneShotDAGNode

class BaseRuntime(ABC):
    """执行后端抽象接口"""
    
    @abstractmethod
    def submit_task(self, task) -> str:
        """提交任务执行，返回任务句柄"""
        pass
    
    @abstractmethod
    def stop_task(self, task_handle: str):
        """停止指定任务"""
        pass
    
    @abstractmethod
    def get_status(self, task_handle: str):
        """获取任务状态"""
        pass

