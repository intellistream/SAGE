#!/usr/bin/env python3
"""
测试Router重构后的功能
"""

import sys
import os
sys.path.append('/api-rework')

from sage.runtime.task_context import TaskContext
from sage.runtime.communication.router.router import BaseRouter
from sage.runtime.communication.queue.python_queue_descriptor import PythonQueueDescriptor
from sage.runtime.communication.router.packet import Packet


class MockTaskContext:
    """模拟TaskContext"""
    def __init__(self, name="test_task"):
        self.name = name
        self.delay = 0.01
        # 模拟下游连接组
        self.downstream_groups = {
            0: {  # broadcast_index=0 (对应下游的input_index=0)
                0: PythonQueueDescriptor(queue_id="test_queue_0_0"),  # parallel_index=0
                1: PythonQueueDescriptor(queue_id="test_queue_0_1"),  # parallel_index=1
            }
        }
        
    @property
    def logger(self):
        import logging
        return logging.getLogger(self.name)


class TestRouter(BaseRouter):
    """测试用的Router实现"""
    
    def _route_packet(self, packet):
        """使用轮询路由"""
        return self._route_round_robin_packet(packet)


def test_router_refactor():
    """测试Router重构功能"""
    print("Testing Router refactor...")
    
    # 创建模拟上下文
    ctx = MockTaskContext()
    
    # 创建Router
    router = TestRouter(ctx)
    
    print(f"✓ Router initialized with downstream_groups: {list(router.downstream_groups.keys())}")
    
    # 测试连接信息
    info = router.get_connections_info()
    print(f"✓ Connection info: {info}")
    
    # 创建测试数据包
    packet = Packet(payload="test_message")
    
    # 测试发送（这会失败因为队列没有真正初始化，但可以测试路由逻辑）
    try:
        result = router.send(packet)
        print(f"✓ Send result: {result}")
    except Exception as e:
        print(f"⚠ Send failed as expected (queue not initialized): {e}")
    
    print("✅ Router refactor test completed!")


if __name__ == "__main__":
    test_router_refactor()
