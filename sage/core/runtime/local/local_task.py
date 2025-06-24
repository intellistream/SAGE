import logging
from re import M
from sage.core.dag.local.dag_node import BaseDAGNode,OneShotDAGNode
from sage.core.dag.local.multi_dag_node import MultiplexerDagNode
from sage.core.dag.local.dag import DAG
import threading

class BaseTask():
    def __init__(self):
        pass

    def execute(self):
        raise NotImplementedError()


class StreamingTask(BaseTask):
    #用于执行流式的数据流
    """
           启动流式处理循环

           Raises:
               TypeError: 当节点类型不匹配时抛出
               RuntimeError: 执行过程中出现错误时抛出
    """
    def __init__(self,node,working_config=None):
        super().__init__()
        self.long_running=True
        self.node=node
        # self.logger=logging.getLogger('streaming_executor')
        self.working_config=working_config or {}
    def execute(self):
        self.logger=logging.getLogger('streaming_executor')
        #循环的执行算子
        try:
            if  isinstance(self.node,MultiplexerDagNode):
                self.node.run_loop()
            else :
                raise TypeError(f"node{self.node.name} is not a MultiplexerDagNode")
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

class OneshotTask(BaseTask):
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
                node._ensure_initialized()
                print(f"Executing node: {node.name}")
                # assert isinstance(node, OneShotDAGNode), f"Expected OneShotDAGNode, got {type(node).__name__}"
                if node.is_spout:
                    # For spout nodes, call operator.receive with dummy channel and data
                    node.operator.receive(0, None)
                else:
                    # For non-spout nodes, fetch input and process
                    input_result = node.fetch_input()
                    
                    # Unpack the tuple: (channel_id, data)
                    channel_id, data = input_result
                    
                    # Call operator's receive method with the channel_id and data
                    node.operator.receive(channel_id, data)

    def stop(self):
        #停止执行
        self.stop_event.set()


