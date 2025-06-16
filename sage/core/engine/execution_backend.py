import logging
from abc import ABC, abstractmethod
import ray
from typing import Dict, List, Optional, Any
from sage.core.engine.executor import StreamingTaskExecutor, OneshotTaskExecutor, BaseTaskExecutor
from sage.core.engine.scheduling_strategy import SchedulingStrategy, ResourceAwareStrategy, PriorityStrategy
from sage.core.dag.dag import DAG
from sage.core.dag.dag_manager import DAGManager
from sage.core.engine.slot import Slot
from sage.core.dag.dag_node import BaseDAGNode, ContinuousDAGNode, OneShotDAGNode

class ExecutionBackend(ABC):
    """执行后端抽象接口"""
    
    @abstractmethod
    def submit_task(self, task: BaseTaskExecutor) -> str:
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

class LocalExecutionBackend(ExecutionBackend):
    """本地线程池执行后端"""
    
    def __init__(self, max_slots=4, scheduling_strategy=None):
        self.available_slots = [Slot(slot_id=i) for i in range(max_slots)]
        self.task_to_slot = {}
        self.task_to_handle = {}  # task -> handle映射
        self.handle_to_task = {}  # handle -> task映射
        self.next_handle_id = 0
        
        if scheduling_strategy is None:
            self.scheduling_strategy = ResourceAwareStrategy()
        else:
            self.scheduling_strategy = scheduling_strategy
    
    def submit_task(self, task: BaseTaskExecutor) -> str:
        """提交任务到本地线程池"""
        slot_id = self.scheduling_strategy.select_slot(task, self.available_slots)
        success = self.available_slots[slot_id].submit_task(task)
        
        if success:
            handle = f"local_task_{self.next_handle_id}"
            self.next_handle_id += 1
            
            self.task_to_slot[task] = slot_id
            self.task_to_handle[task] = handle
            self.handle_to_task[handle] = task
            return handle
        else:
            raise RuntimeError(f"Failed to submit task to slot {slot_id}")
    
    def stop_task(self, task_handle: str):
        """停止本地任务"""
        if task_handle not in self.handle_to_task:
            return
            
        task = self.handle_to_task[task_handle]
        slot_id = self.task_to_slot[task]
        self.available_slots[slot_id].stop(task)
        
        # 清理映射关系
        self.task_to_slot.pop(task, None)
        self.task_to_handle.pop(task, None)
        self.handle_to_task.pop(task_handle, None)
    
    def get_status(self, task_handle: str):
        """获取本地任务状态"""
        if task_handle not in self.handle_to_task:
            return {"status": "not_found"}
        return {"status": "running", "backend": "local"}

@ray.remote
class RayTaskActor:
    """Ray任务执行Actor"""
    
    def execute_task(self, task: BaseTaskExecutor):
        """在Ray Actor中执行任务"""
        return task.execute()
    
    def stop_task(self):
        """停止任务执行"""
        # 实现停止逻辑
        pass

