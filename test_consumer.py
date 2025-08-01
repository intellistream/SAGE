#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'sage_ext/sage_queue/tests/stress')

# 测试消费者工作函数
from sage_ext.sage_queue.tests.stress.test_multiprocess_stress import stress_consumer_worker_func

# 先创建一个队列并放入一些数据
from sage_ext.sage_queue.python.sage_queue import SageQueue
queue = SageQueue('test_consumer_queue', 1024)
queue.put(b'test message 1', timeout=1.0)
queue.put(b'test message 2', timeout=1.0)
queue.close()

# 测试单个消费者
result = stress_consumer_worker_func(0, ['test_consumer_queue'], 2, 5)
print('Consumer result:', result)
