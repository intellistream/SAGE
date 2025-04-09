import logging

from sage.core.engine.executor import StreamingExecutor, OneShotExecutor
from sage.core.engine.scheduling_strategy import SchedulingStrategy, ResourceAwareStrategy, PriorityStrategy
from sage.core.dag.dag import DAG
from sage.core.dag.dag_manager import DAGManager
from sage.core.engine.slot import Slot
from sage.core.dag.dag_node import BaseDAGNode,ContinuousDAGNode,OneShotDAGNode
import time

class ExecutorManager:
    """用于管理任务，初始化slots,并负责将任务提交到slot里面运行，基于已提交的dag提取出所有的node并根据node按照一定的策略分配给不同的slot
     Attributes:
        available_slots (List[Slot]): 可用计算槽位列表
        max_slots (int): 最大槽位数量
        dag_manager (DAGManager): DAG流程管理器
        task_to_slot (Dict[object, int]): 任务到槽位的映射关系
        dag_to_tasks (Dict[str, List[object]]): DAG到其关联任务的映射
        logger (logging.Logger): 日志记录器
        scheduling_strategy (SchedulingStrategy): 任务调度策略实现
    """
    def __init__(self,dag_manager:DAGManager, max_slots=4,scheduling_strategy=None):
        self.available_slots = [Slot(slot_id=i) for i in range(max_slots)]
        self.max_slots = max_slots
        self.dag_manager = dag_manager
        self.task_to_slot ={}
        self.dag_to_tasks={}
        self.logger=logging.getLogger(__name__)
        if scheduling_strategy is None:
            self.scheduling_strategy = ResourceAwareStrategy()
        elif scheduling_strategy.lower() =="prioritystrategy":
            self.scheduling_strategy = PriorityStrategy({})
        else :
            self.scheduling_strategy = ResourceAwareStrategy()


    def submit_dag(self):
        """
        提交DAG并调度其节点

        流程：
        1. 从DAG管理器获取正在运行的DAG列表
        2. 清空管理器的运行中DAG记录（避免重复提交）
        3. 对每个DAG创建对应任务：
           - 流式DAG：为每个节点创建独立任务
           - 一次性DAG：为整个DAG创建单个任务
        4. 将任务分配到可用槽位执行
        """
        running_dags=self.dag_manager.get_running_dags()
        self.dag_manager.clear_running_dags()
        for dag_id in running_dags:
            # if self.dag_to_tasks.get(dag_id) is None :
                self.dag_to_tasks[dag_id]=[]
                dag=self.dag_manager.get_dag(dag_id)
                if dag.strategy=="streaming" :
                    for node in dag.nodes:
                        task=self.create_streaming_task(node)
                        slot_id=self.schedule_task(task)
                        self.dag_to_tasks[dag_id].append(task)
                        self.task_to_slot[task]=slot_id
                        self.available_slots[slot_id].submit_task(task)
                        self.logger.debug(f"{node.name} submitted task for slot {slot_id}")
                else :
                    task=self.create_oneshot_task(dag)
                    slot_id=self.schedule_task(task)
                    self.dag_to_tasks[dag_id].append(task)
                    self.task_to_slot[task]=slot_id
                    self.available_slots[slot_id].submit_task(task)
                    self.logger.debug(f"dag submitted task for slot {slot_id}")

    def create_streaming_task(self,node) :
        """
          创建流式处理任务

          Args:
              node: DAG节点对象

          Returns:
              StreamingExecutor: 流式执行器实例
          """
        streaming_executor=StreamingExecutor(node)
        return streaming_executor

    def create_oneshot_task(self,dag):
        """
           创建一次性处理任务

           Args:
               dag: 需要处理的DAG对象

           Returns:
               OneShotExecutor: 一次性执行器实例
           """
        oneshot_executor=OneShotExecutor(dag)
        return oneshot_executor

    def schedule_task(self, task) -> int :
            """
               调度任务到指定槽位

               Args:
                   task: 需要调度的任务对象

               Returns:
                   int: 分配的槽位ID

               Raises:
                   RuntimeError: 当无可用槽位时抛出
               """
            selected_slot_id = self.scheduling_strategy.select_slot(
                task, self.available_slots
            )
            self.logger.info(f"chosen slot id {selected_slot_id}")
            if selected_slot_id > 0 :
                self.available_slots[selected_slot_id].submit_task(task)
                self.task_to_slot[task] = selected_slot_id
            return selected_slot_id

    def stop_dag(self,dag_id):
        """
            停止指定DAG的所有任务

            Args:
                dag_id: 要停止的DAG标识符

            流程：
                1. 获取DAG关联的所有任务
                2. 停止每个任务并释放槽位资源
                3. 清理任务记录
        """
        tasks=self.dag_to_tasks[dag_id]
        for task in tasks:
            slot_id=self.task_to_slot[task]
            slot=self.available_slots[slot_id]
            slot.stop(task)
            self.task_to_slot.pop(task)
        self.dag_to_tasks.pop(dag_id)
        self.dag_manager.remove_from_running(dag_id)


