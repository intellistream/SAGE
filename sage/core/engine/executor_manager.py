from asyncio import create_task
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Dict, Optional, List
import logging

from sage.core.engine.executor import StreamingExecutor, OneShotExecutor
from sage.core.engine.scheduling_strategy import SchedulingStrategy, ResourceAwareStrategy, PriorityStrategy
from sage.core.dag.dag import DAG
from sage.core.dag.dag_manager import DAGManager
from sage.core.engine.slot import Slot
from sage.core.dag.dag_node import BaseDAGNode,ContinuousDAGNode,OneShotDAGNode
import time

class ExecutorManager:
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
        """提交DAG并调度其节点"""
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
        streaming_executor=StreamingExecutor(node)
        return streaming_executor

    def create_oneshot_task(self,dag):
        oneshot_executor=OneShotExecutor(dag)
        return oneshot_executor

    def schedule_task(self, task) -> int :

            selected_slot_id = self.scheduling_strategy.select_slot(
                task, self.available_slots
            )
            self.logger.info(f"chosen slot id {selected_slot_id}")
            if selected_slot_id > 0 :
                self.available_slots[selected_slot_id].submit_task(task)
                self.task_to_slot[task] = selected_slot_id
            return selected_slot_id

    def stop_dag(self,dag_id):
        tasks=self.dag_to_tasks[dag_id]
        for task in tasks:
            slot_id=self.task_to_slot[task]
            slot=self.available_slots[slot_id]
            slot.stop(task)
            self.task_to_slot.pop(task)
        self.dag_to_tasks.pop(dag_id)
        self.dag_manager.remove_from_running(dag_id)


