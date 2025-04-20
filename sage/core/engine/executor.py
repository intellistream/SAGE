import logging
from sage.core.dag.dag_node import BaseDAGNode,ContinuousDAGNode,OneShotDAGNode
from sage.core.dag.dag import DAG
import threading

class BaseExecutor():
    def __init__(self):
        pass

    def execute(self):
        raise NotImplementedError()


class StreamingExecutor(BaseExecutor):
    #用于执行流式的数据流
    """
           启动流式处理循环

           Raises:
               TypeError: 当节点类型不匹配时抛出
               RuntimeError: 执行过程中出现错误时抛出
    """
    def __init__(self,node:ContinuousDAGNode,working_config=None):
        super().__init__()
        self.long_running=True
        self.node=node
        self.logger=logging.getLogger('streaming_executor')
        self.working_config=working_config or {}
    def execute(self):
        #循环的执行算子
        try:
            if  isinstance(self.node,ContinuousDAGNode):
                self.node.run_loop()
            else :
                raise TypeError(f"node{self.node.name} is not a ContinuousDAGNode")
        except Exception as e:
            self.logger.error(e)
            raise TypeError(e)

    def stop(self):
        #停止该executor的执行
        try:
            self.node.stop()
        except Exception as e:
            self.logger.error(e)
            raise RuntimeError(e)

class OneShotExecutor(BaseExecutor):
    #用于执行非流式的请求
    """
        一次性任务处理器，按拓扑顺序执行DAG流程

        Attributes:
            dag (DAG): 需要处理的DAG对象
            stop_event (threading.Event): 任务停止信号量
        """
    def __init__(self,dag:DAG):
        super().__init__()
        self.dag=dag
        self.long_running=False
        self.logger=logging.getLogger('oneshot executor')
        self.stop_event=threading.Event()
    def execute(self):
        #遍历按序执行每一个算子
            for node in self.dag.get_topological_order():
                if not self.stop_event.is_set():
                    assert isinstance(node, OneShotDAGNode), f"Expected OneShotDAGNode, got {type(node).__name__}"
                    node.execute()
    def stop(self):
        #停止执行
        self.stop_event.set()


        
