#!/usr/bin/env python3
"""
测试队列描述符集成功能
"""

import sys
import os
sys.path.append('/api-rework')

from sage.runtime.service_context import RuntimeContext
from sage.runtime.communication.queue_creation_strategy import QueueCreationStrategy

def test_queue_descriptor_integration():
    """测试队列描述符集成"""
    print("Testing Queue Descriptor Integration...")
    
    # 测试队列创建策略
    strategy = QueueCreationStrategy()
    
    # 测试本地队列创建
    local_input_queue = strategy.create_task_input_queue("test_task", is_remote=False)
    print(f"✓ Created local input queue: {local_input_queue.queue_id} (type: {local_input_queue.queue_type})")
    
    local_service_request_queue = strategy.create_service_request_queue("test_service", is_remote=False)
    print(f"✓ Created local service request queue: {local_service_request_queue.queue_id} (type: {local_service_request_queue.queue_type})")
    
    local_service_response_queue = strategy.create_service_response_queue("test_service", "test_node", is_remote=False)
    print(f"✓ Created local service response queue: {local_service_response_queue.queue_id} (type: {local_service_response_queue.queue_type})")
    
    # 测试远程队列创建
    try:
        import ray
        if not ray.is_initialized():
            print("⚠ Ray not initialized, skipping remote queue tests")
        else:
            remote_input_queue = strategy.create_task_input_queue("test_task", is_remote=True)
            print(f"✓ Created remote input queue: {remote_input_queue.queue_id} (type: {remote_input_queue.queue_type})")
    except (ImportError, RuntimeError) as e:
        print(f"⚠ Ray not available or version mismatch, skipping remote queue tests: {e}")
    
    # 测试默认参数
    local_params = strategy.get_default_queue_params(is_remote=False)
    remote_params = strategy.get_default_queue_params(is_remote=True)
    print(f"✓ Local params: {local_params}")
    print(f"✓ Remote params: {remote_params}")
    
    print("Queue Descriptor Integration Test Passed! ✓")

if __name__ == "__main__":
    test_queue_descriptor_integration()