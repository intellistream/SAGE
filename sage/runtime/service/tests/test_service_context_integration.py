"""
BaseServiceTask与ServiceContext集成测试

测试BaseServiceTask在真实的ServiceContext环境中的工作情况，
包括与BaseQueueDescriptor的集成。
"""

import unittest
import threading
import time
import queue
from unittest.mock import Mock, patch
from typing import Dict, Any

from sage.runtime.service.base_service_task import BaseServiceTask
from sage.runtime.service_context import ServiceContext
from sage.runtime.factory.service_factory import ServiceFactory


class MockEnvironment:
    """模拟环境"""
    
    def __init__(self):
        self.name = "test_env"
        self.env_base_dir = "/tmp/test"
        self.console_log_level = "INFO"


class MockServiceNode:
    """模拟ServiceNode"""
    
    def __init__(self, name: str):
        self.name = name
        self.service_qd = None  # 请求队列描述符
        

class MockExecutionGraph:
    """模拟ExecutionGraph"""
    
    def __init__(self):
        self.nodes = {}
    
    def add_node(self, name: str, node):
        self.nodes[name] = node


class PythonQueueDescriptor:
    """Python Queue 描述符实现"""
    
    def __init__(self, queue_id: str = None, maxsize: int = 100):
        self.queue_id = queue_id or f"python_queue_{id(self)}"
        self.queue_type = "python_queue"
        self.can_serialize = True
        self.metadata = {"maxsize": maxsize}
        self._queue_instance = None
        self._initialized = False
        self.created_timestamp = time.time()
    
    @property
    def queue_instance(self):
        if not self._initialized:
            self._queue_instance = queue.Queue(maxsize=self.metadata["maxsize"])
            self._initialized = True
        return self._queue_instance
    
    def put(self, item, block=True, timeout=None):
        return self.queue_instance.put(item, block=block, timeout=timeout)
    
    def get(self, block=True, timeout=None):
        return self.queue_instance.get(block=block, timeout=timeout)
    
    def get_nowait(self):
        return self.queue_instance.get_nowait()
    
    def put_nowait(self, item):
        return self.queue_instance.put_nowait(item)
    
    def empty(self):
        return self.queue_instance.empty()
    
    def qsize(self):
        return self.queue_instance.qsize()


class MockTestService:
    """测试服务实现"""
    
    def __init__(self):
        self.processed_requests = []
        self.setup_called = False
        self.cleanup_called = False
    
    def setup(self):
        self.setup_called = True
    
    def cleanup(self):
        self.cleanup_called = True
    
    def echo(self, message):
        """简单的echo方法"""
        result = f"echo: {message}"
        self.processed_requests.append(result)
        return result
    
    def add(self, a, b):
        """数学加法"""
        result = a + b
        self.processed_requests.append(f"add({a}, {b}) = {result}")
        return result
    
    def error_method(self):
        """总是抛出错误的方法"""
        raise RuntimeError("Intentional test error")


class MockTestServiceFactory:
    """测试服务工厂"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.service_class = MockTestService
    
    def create_service(self, ctx):
        return MockTestService()


class ConcreteTestServiceTask(BaseServiceTask):
    """测试用的具体ServiceTask实现"""
    
    def __init__(self, service_factory, ctx=None):
        super().__init__(service_factory, ctx)
        self.start_called = False
        self.stop_called = False
    
    def _start_service_instance(self):
        self.start_called = True
    
    def _stop_service_instance(self):
        self.stop_called = True


class TestServiceContextIntegration(unittest.TestCase):
    """测试ServiceContext集成"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建环境和节点
        self.env = MockEnvironment()
        self.service_node = MockServiceNode("test_service")
        self.execution_graph = MockExecutionGraph()
        
        # 创建队列描述符
        self.request_qd = PythonQueueDescriptor("request_queue", maxsize=50)
        self.response_qd = PythonQueueDescriptor("response_queue", maxsize=50)
        
        # 设置service node的队列描述符
        self.service_node.service_qd = self.request_qd
        
        # 创建响应节点并添加到执行图
        response_node = Mock()
        response_node.service_response_qd = self.response_qd
        self.execution_graph.add_node("response_node", response_node)
        
        # 创建ServiceContext
        self.service_context = ServiceContext(
            self.service_node, 
            self.env, 
            self.execution_graph
        )
        
        # 创建服务工厂和任务
        self.service_factory = MockTestServiceFactory("test_service")
        self.service_task = ConcreteTestServiceTask(
            self.service_factory, 
            self.service_context
        )
    
    def test_service_context_queue_integration(self):
        """测试ServiceContext队列集成"""
        # 验证ServiceContext正确设置了队列描述符
        self.assertEqual(
            self.service_context.get_request_queue_descriptor(), 
            self.request_qd
        )
        
        response_qds = self.service_context.get_service_response_queue_descriptors()
        self.assertEqual(len(response_qds), 1)
        self.assertIn("response_node", response_qds)
        
        # 验证ServiceTask能够访问队列
        self.assertEqual(
            self.service_task.request_queue_descriptor, 
            self.request_qd
        )
        self.assertEqual(
            self.service_task.request_queue, 
            self.request_qd.queue_instance
        )
        
        response_queue = self.service_task.get_response_queue("response_node")
        self.assertEqual(response_queue, self.response_qd.queue_instance)
    
    def test_end_to_end_request_processing(self):
        """测试端到端请求处理"""
        # 启动服务任务
        self.service_task.start_running()
        self.assertTrue(self.service_task.is_running)
        self.assertTrue(self.service_task.start_called)
        
        # 等待队列监听器启动
        time.sleep(0.1)
        
        # 发送测试请求
        test_requests = [
            {
                'request_id': 'req_001',
                'method_name': 'echo',
                'args': ('Hello World',),
                'kwargs': {},
                'response_queue': 'response_node',
                'timeout': 10.0
            },
            {
                'request_id': 'req_002',
                'method_name': 'add',
                'args': (5, 3),
                'kwargs': {},
                'response_queue': 'response_node',
                'timeout': 10.0
            },
            {
                'request_id': 'req_003',
                'method_name': 'error_method',
                'args': (),
                'kwargs': {},
                'response_queue': 'response_node',
                'timeout': 10.0
            }
        ]
        
        # 发送所有请求
        for request in test_requests:
            self.request_qd.put(request)
        
        # 等待处理
        time.sleep(0.5)
        
        # 验证响应
        responses = []
        while not self.response_qd.empty():
            responses.append(self.response_qd.queue_instance.get_nowait())
        
        self.assertEqual(len(responses), 3)
        
        # 验证第一个响应 (echo)
        echo_response = next(r for r in responses if r['request_id'] == 'req_001')
        self.assertTrue(echo_response['success'])
        self.assertEqual(echo_response['result'], 'echo: Hello World')
        self.assertIsNone(echo_response['error'])
        
        # 验证第二个响应 (add)
        add_response = next(r for r in responses if r['request_id'] == 'req_002')
        self.assertTrue(add_response['success'])
        self.assertEqual(add_response['result'], 8)
        self.assertIsNone(add_response['error'])
        
        # 验证第三个响应 (error)
        error_response = next(r for r in responses if r['request_id'] == 'req_003')
        self.assertFalse(error_response['success'])
        self.assertIsNone(error_response['result'])
        self.assertEqual(error_response['error'], 'Intentional test error')
        
        # 停止服务任务
        self.service_task.stop()
        self.assertFalse(self.service_task.is_running)
        self.assertTrue(self.service_task.stop_called)
    
    def test_concurrent_request_processing(self):
        """测试并发请求处理"""
        self.service_task.start_running()
        time.sleep(0.1)
        
        # 创建多个并发请求
        num_requests = 20
        requests = []
        for i in range(num_requests):
            requests.append({
                'request_id': f'concurrent_req_{i:03d}',
                'method_name': 'add',
                'args': (i, i * 2),
                'kwargs': {},
                'response_queue': 'response_node',
                'timeout': 10.0
            })
        
        # 快速发送所有请求
        for request in requests:
            self.request_qd.put(request)
        
        # 等待处理完成
        time.sleep(1.0)
        
        # 收集所有响应
        responses = []
        while not self.response_qd.empty():
            responses.append(self.response_qd.queue_instance.get_nowait())
        
        # 验证所有请求都被处理
        self.assertEqual(len(responses), num_requests)
        
        # 验证所有响应都成功
        for response in responses:
            self.assertTrue(response['success'])
            self.assertIsNone(response['error'])
        
        # 验证结果正确性
        for i in range(num_requests):
            req_id = f'concurrent_req_{i:03d}'
            response = next(r for r in responses if r['request_id'] == req_id)
            expected_result = i + (i * 2)  # add(i, i*2)
            self.assertEqual(response['result'], expected_result)
        
        self.service_task.stop()
    
    def test_service_statistics_integration(self):
        """测试服务统计信息集成"""
        # 启动服务并处理一些请求
        self.service_task.start_running()
        time.sleep(0.1)
        
        # 发送几个请求
        for i in range(5):
            request = {
                'request_id': f'stats_req_{i}',
                'method_name': 'echo',
                'args': (f'message_{i}',),
                'kwargs': {},
                'response_queue': 'response_node',
                'timeout': 10.0
            }
            self.request_qd.put(request)
        
        time.sleep(0.3)
        
        # 获取统计信息
        stats = self.service_task.get_statistics()
        
        # 验证基本统计
        self.assertEqual(stats['service_name'], 'test_service')
        self.assertTrue(stats['is_running'])
        self.assertEqual(stats['request_count'], 5)
        self.assertEqual(stats['error_count'], 0)
        
        # 验证ServiceContext集成统计
        self.assertTrue(stats['has_service_context'])
        self.assertTrue(stats['request_queue_available'])
        self.assertEqual(stats['request_queue_type'], 'python_queue')
        self.assertEqual(stats['response_queues_count'], 1)
        self.assertEqual(stats['response_queue_names'], ['response_node'])
        
        self.service_task.stop()
    
    def test_cleanup_with_service_context(self):
        """测试与ServiceContext的清理集成"""
        # 启动服务
        self.service_task.start_running()
        original_request_queue = self.service_task.request_queue
        original_response_queue = self.service_task.get_response_queue("response_node")
        
        # 执行清理
        self.service_task.cleanup()
        
        # 验证服务任务状态
        self.assertFalse(self.service_task.is_running)
        self.assertTrue(self.service_task.service_instance.cleanup_called)
        
        # 验证队列仍然可用（由ServiceContext管理）
        self.assertIsNotNone(self.service_task.request_queue)
        self.assertIsNotNone(self.service_task.get_response_queue("response_node"))
        
        # 队列实例应该保持相同（没有被清理）
        self.assertEqual(self.service_task.request_queue, original_request_queue)
        self.assertEqual(
            self.service_task.get_response_queue("response_node"), 
            original_response_queue
        )


if __name__ == '__main__':
    unittest.main()
