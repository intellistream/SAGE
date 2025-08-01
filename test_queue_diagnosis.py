#!/usr/bin/env python3
import sys
import os
import time
sys.path.insert(0, 'sage_ext/sage_queue/tests/stress')

from sage_ext.sage_queue.python.sage_queue import SageQueue

def test_basic_queue_operations():
    print("=== 基本队列操作测试 ===")
    
    # 测试1: 基本的 put/get
    print("测试1: 基本 put/get")
    queue = SageQueue('basic_test', 1024)
    
    # 放入数据
    success = queue.put(b'hello world', timeout=1.0)
    print(f"Put success: {success}")
    
    # 获取数据
    data = queue.get(timeout=1.0)
    print(f"Got data: {data}")
    
    queue.close()
    print("测试1 完成\n")
    
    # 测试2: 同一个队列名的跨实例访问
    print("测试2: 跨实例访问")
    
    # 创建第一个实例并放入数据
    queue1 = SageQueue('cross_instance_test', 1024)
    success = queue1.put(b'cross instance message', timeout=1.0)
    print(f"Queue1 put success: {success}")
    
    # 不关闭queue1，创建第二个实例尝试读取
    queue2 = SageQueue('cross_instance_test', 1024)  # 同样的名称
    data = queue2.get(timeout=1.0)
    print(f"Queue2 got data: {data}")
    
    queue1.close()
    queue2.close()
    print("测试2 完成\n")
    
    # 测试3: 关闭后重新打开
    print("测试3: 关闭后重新打开")
    
    # 创建队列，放入数据，然后关闭
    queue3 = SageQueue('reopen_test', 1024)
    success = queue3.put(b'persistent message', timeout=1.0)
    print(f"Queue3 put success: {success}")
    queue3.close()
    
    # 重新打开同名队列尝试读取
    queue4 = SageQueue('reopen_test', 1024)
    data = queue4.get(timeout=1.0)
    print(f"Queue4 got data after reopen: {data}")
    queue4.close()
    print("测试3 完成\n")

if __name__ == "__main__":
    test_basic_queue_operations()
