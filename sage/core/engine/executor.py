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
    def __init__(self,node:ContinuousDAGNode):
        super().__init__()
        self.long_running=True
        self.node=node
        self.logger=logging.getLogger('streaming executor')
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


        
