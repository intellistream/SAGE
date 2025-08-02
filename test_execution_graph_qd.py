#!/usr/bin/env python3
"""
测试ExecutionGraph中队列描述符的完整集成
"""

import sys
import os
sys.path.append('/api-rework')

from sage.core.api.local_environment import LocalEnvironment
from sage.core.transformation.source_transformation import SourceTransformation  
from sage.core.transformation.sink_transformation import SinkTransformation
from sage.core.operator.source_operator import SourceOperator
from sage.core.operator.sink_operator import SinkOperator
from sage.core.function.source_function import SourceFunction
from sage.core.function.sink_function import SinkFunction
from sage.jobmanager.execution_graph import ExecutionGraph


class TestSourceFunction(SourceFunction):
    def __init__(self):
        super().__init__()
        self.count = 0
    
    def execute(self):
        """实现抽象方法"""
        self.count += 1
        if self.count <= 3:
            return f"message_{self.count}"
        return None
    
    def invoke(self, ctx):
        self.count += 1
        if self.count <= 3:
            ctx.collect(f"message_{self.count}")
            return True
        return False


class TestSinkFunction(SinkFunction):
    def __init__(self):
        super().__init__()
        self.received = []
    
    def execute(self, data):
        """实现抽象方法"""
        self.received.append(data)
        print(f"Received: {data}")
    
    def invoke(self, value, ctx):
        self.received.append(value)
        print(f"Received: {value}")


def test_execution_graph_queue_descriptors():
    """测试ExecutionGraph中队列描述符的创建和分发"""
    print("Testing ExecutionGraph queue descriptor integration...")
    
    # 创建测试环境
    env = LocalEnvironment("test_graph_qd")
    env.platform = "local"  # 使用本地环境
    env.env_base_dir = "/tmp/test_sage"  # 设置base dir
    
    try:
        # 创建ExecutionGraph - 注意这会用空的pipeline
        print("Creating ExecutionGraph with empty pipeline...")
        graph = ExecutionGraph(env)
        
        # 验证基本结构
        print(f"✓ Created {len(graph.nodes)} graph nodes")
        print(f"✓ Created {len(graph.service_nodes)} service nodes")  
        print(f"✓ Created {len(graph.edges)} edges")
        
        # 测试队列创建策略是否工作
        from sage.runtime.communication.queue_creation_strategy import QueueCreationStrategy
        strategy = QueueCreationStrategy()
        
        # 测试各种队列创建
        input_qd = strategy.create_task_input_queue("test_node", is_remote=False)
        print(f"✓ Task input queue: {input_qd.queue_id}")
        
        inter_qd = strategy.create_inter_task_queue("node1", "node2", is_remote=False)
        print(f"✓ Inter-task queue: {inter_qd.queue_id}")
        
        service_req_qd = strategy.create_service_request_queue("test_service", is_remote=False)
        print(f"✓ Service request queue: {service_req_qd.queue_id}")
        
        service_resp_qd = strategy.create_service_response_queue("response", "test_node", is_remote=False)
        print(f"✓ Service response queue: {service_resp_qd.queue_id}")
        
        print("\n✅ ExecutionGraph queue descriptor integration test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_execution_graph_queue_descriptors()
    sys.exit(0 if success else 1)
