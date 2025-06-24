from sage.core.runtime import BaseRuntime
from sage.core.runtime.local.local_scheduling_strategy import SchedulingStrategy, ResourceAwareStrategy, PriorityStrategy
from sage.core.runtime.local.local_task import StreamingTask, OneshotTask, BaseTask
from sage.core.runtime.local.local_slot import Slot
import logging

class LocalRuntime(BaseRuntime):
    """本地线程池执行后端"""
    
    def __init__(self, max_slots=4, scheduling_strategy=None):
        self.name = "LocalRuntime"
        self.available_slots = [Slot(slot_id=i) for i in range(max_slots)]
        self.task_to_slot = {}
        self.task_to_handle = {}  # task -> handle映射
        self.handle_to_task = {}  # handle -> task映射
        self.next_handle_id = 0
        self.logger = logging.getLogger("LocalRuntime")
        
        if scheduling_strategy is None:
            self.scheduling_strategy = ResourceAwareStrategy()
        else:
            self.scheduling_strategy = scheduling_strategy
    
    def submit_task(self, local_dag):
        """
        提交到本地后端执行
        
        Args:
            local_dag: local_dag 实例
            
        Returns:
            str: 任务句柄
        """

        for node in local_dag.nodes:

            task = StreamingTask(node, local_dag.working_config)
            task_handle = self.submit_node(task)
            #self.task_handles[dag_id].append(task_handle)
            self.logger.debug(f"DAGNode {node.name} submitted to {self.name} with handle: {task_handle}")
    
        


    def submit_node(self, task: BaseTask) -> str:
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
