"""
测试BaseServiceTask的队列管理重构

验证BaseServiceTask正确使用ServiceContext中的队列描述符，
而不是自己创建和管理队列。
"""

import unittest
import threading
import time
import queue
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from sage.runtime.service.base_service_task import BaseServiceTask
from sage.runtime.service_context import ServiceContext
from sage.runtime.factory.service_factory import ServiceFactory
from sage.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor


class MockQueueDescriptor(BaseQueueDescriptor):
    """模拟队列描述符"""
    
    def __init__(self, queue_id: str = None, mock_queue=None):
        self._mock_queue = mock_queue or queue.Queue(maxsize=100)
        super().__init__(queue_id)
    
    @property
    def queue_type(self) -> str:
        return "mock_queue"
    
    @property
    def can_serialize(self) -> bool:
        return True
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return {"maxsize": 100, "mock": True}
    
    @property
    def queue_instance(self):
        return self._mock_queue


class MockService:
    """模拟服务类"""
    
    def __init__(self):
        self.call_count = 0
        self.setup_called = False
        self.cleanup_called = False
    
    def setup(self):
        self.setup_called = True
    
    def cleanup(self):
        self.cleanup_called = True
    
    def test_method(self, value):
        self.call_count += 1
        return f"processed_{value}"
    
    def failing_method(self):
        raise ValueError("Test error")


class MockServiceFactory:
    """模拟服务工厂"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.service_class = MockService
        self._service_instance = None
    
    def create_service(self, ctx):
        if self._service_instance is None:
            self._service_instance = MockService()
        return self._service_instance


class MockServiceContext:
    """模拟ServiceContext"""
    
    def __init__(self, name: str = "test_service"):
        self.name = name
        self._request_qd = None
        self._response_qds = {}
        self._logger = Mock()
    
    @property
    def logger(self):
        return self._logger
    
    def set_request_queue_descriptor(self, qd: BaseQueueDescriptor):
        self._request_qd = qd
    
    def get_request_queue_descriptor(self):
        return self._request_qd
    
    def set_service_response_queue_descriptors(self, qds: Dict[str, BaseQueueDescriptor]):
        self._response_qds = qds
    
    def get_service_response_queue_descriptors(self):
        return self._response_qds
    
    def get_service_response_queue_descriptor(self, node_name: str):
        return self._response_qds.get(node_name)


class ConcreteServiceTask(BaseServiceTask):
    """具体的ServiceTask实现，用于测试"""
    
    def __init__(self, service_factory, ctx=None):
        super().__init__(service_factory, ctx)
        self.started = False
        self.stopped = False
    
    def _start_service_instance(self):
        self.started = True
    
    def _stop_service_instance(self):
        self.stopped = True


class TestBaseServiceTaskQueueManagement(unittest.TestCase):
    """测试BaseServiceTask的队列管理重构"""
    
    def setUp(self):
        """设置测试环境"""
        self.service_name = "test_service"
        self.service_factory = MockServiceFactory(self.service_name)
        self.service_context = MockServiceContext(self.service_name)
        
        # 创建队列描述符
        self.request_queue = queue.Queue(maxsize=100)
        self.request_qd = MockQueueDescriptor("request_queue", self.request_queue)
        
        self.response_queue = queue.Queue(maxsize=100)
        self.response_qd = MockQueueDescriptor("response_queue", self.response_queue)
        
        # 设置ServiceContext中的队列描述符
        self.service_context.set_request_queue_descriptor(self.request_qd)
        self.service_context.set_service_response_queue_descriptors({
            "target_node": self.response_qd
        })
        
        # 创建ServiceTask实例
        self.service_task = ConcreteServiceTask(self.service_factory, self.service_context)
    
    def test_initialization_with_service_context(self):
        """测试使用ServiceContext初始化"""
        # 验证ServiceTask正确引用了ServiceContext
        self.assertEqual(self.service_task.ctx, self.service_context)
        self.assertEqual(self.service_task.service_name, self.service_name)
        
        # 验证服务实例创建
        self.assertIsInstance(self.service_task.service_instance, MockService)
        self.assertTrue(self.service_task.service_instance.setup_called)
    
    def test_queue_descriptor_access(self):
        """测试队列描述符访问方法"""
        # 测试请求队列描述符访问
        request_qd = self.service_task.request_queue_descriptor
        self.assertEqual(request_qd, self.request_qd)
        
        # 测试请求队列实例访问
        request_queue = self.service_task.request_queue
        self.assertEqual(request_queue, self.request_queue)
        
        # 测试响应队列描述符访问
        response_qd = self.service_task.get_response_queue_descriptor("target_node")
        self.assertEqual(response_qd, self.response_qd)
        
        # 测试响应队列实例访问
        response_queue = self.service_task.get_response_queue("target_node")
        self.assertEqual(response_queue, self.response_queue)
    
    def test_queue_access_without_context(self):
        """测试没有ServiceContext时的队列访问"""
        task_without_ctx = ConcreteServiceTask(self.service_factory, None)
        
        # 应该返回None
        self.assertIsNone(task_without_ctx.request_queue_descriptor)
        self.assertIsNone(task_without_ctx.request_queue)
        self.assertIsNone(task_without_ctx.get_response_queue_descriptor("any_node"))
        self.assertIsNone(task_without_ctx.get_response_queue("any_node"))
    
    def test_service_request_handling(self):
        """测试服务请求处理"""
        # 准备测试请求 - 使用 response_queue 对象而不是名称
        request_data = {
            'request_id': 'test_001',
            'method_name': 'test_method',
            'args': ('test_value',),
            'kwargs': {},
            'response_queue': self.response_queue,  # 直接传递队列对象
            'timeout': 30.0
        }
        
        # 调用handle_request方法（这个方法支持直接的队列对象）
        self.service_task.handle_request(request_data)
        
        # 验证服务方法被调用
        self.assertEqual(self.service_task.service_instance.call_count, 1)
        
        # 检查响应队列中是否有响应 - 添加小延迟确保异步操作完成
        import time
        time.sleep(0.1)  # 给异步操作一点时间
        
        self.assertFalse(self.response_queue.empty(), "Response queue should not be empty after handling request")
        response = self.response_queue.get_nowait()
        
        # 验证响应数据
        self.assertEqual(response['request_id'], 'test_001')
        self.assertTrue(response['success'])
        self.assertEqual(response['result'], 'processed_test_value')
        self.assertIsNone(response['error'])
    
    def test_service_request_error_handling(self):
        """测试服务请求错误处理"""
        request_data = {
            'request_id': 'test_002',
            'method_name': 'failing_method',
            'args': (),
            'kwargs': {},
            'response_queue': self.response_queue,  # 直接传递队列对象
            'timeout': 30.0
        }
        
        self.service_task.handle_request(request_data)
        
        # 添加小延迟确保异步操作完成
        import time
        time.sleep(0.1)
        
        # 检查响应队列不为空
        self.assertFalse(self.response_queue.empty(), "Response queue should not be empty after handling error request")
        response = self.response_queue.get_nowait()
        self.assertEqual(response['request_id'], 'test_002')
        self.assertFalse(response['success'])
        self.assertIsNone(response['result'])
        self.assertEqual(response['error'], 'Test error')
    
    def test_queue_listener_integration(self):
        """测试队列监听功能"""
        # 启动服务任务
        self.service_task.start_running()
        self.assertTrue(self.service_task.is_running)
        self.assertTrue(self.service_task.started)
        
        # 等待队列监听线程启动
        time.sleep(0.1)
        
        # 向请求队列发送请求
        request_data = {
            'request_id': 'queue_test_001',
            'method_name': 'test_method',
            'args': ('queue_value',),
            'kwargs': {},
            'response_queue': 'target_node',
            'timeout': 30.0
        }
        
        self.request_queue.put(request_data)
        
        # 等待处理
        time.sleep(0.2)
        
        # 验证响应
        self.assertFalse(self.response_queue.empty())
        response = self.response_queue.get_nowait()
        self.assertEqual(response['request_id'], 'queue_test_001')
        self.assertTrue(response['success'])
        self.assertEqual(response['result'], 'processed_queue_value')
        
        # 停止服务任务
        self.service_task.stop()
        self.assertFalse(self.service_task.is_running)
        self.assertTrue(self.service_task.stopped)
    
    def test_statistics_with_service_context(self):
        """测试统计信息包含ServiceContext队列信息"""
        stats = self.service_task.get_statistics()
        
        # 验证基本统计信息
        self.assertEqual(stats['service_name'], self.service_name)
        self.assertEqual(stats['service_type'], 'ConcreteServiceTask')
        self.assertTrue(stats['has_service_context'])
        
        # 验证队列相关统计信息
        self.assertTrue(stats['request_queue_available'])
        self.assertEqual(stats['request_queue_id'], self.request_qd.queue_id)
        self.assertEqual(stats['request_queue_type'], 'mock_queue')
        self.assertEqual(stats['response_queues_count'], 1)
        self.assertEqual(stats['response_queue_names'], ['target_node'])
    
    def test_statistics_without_service_context(self):
        """测试没有ServiceContext时的统计信息"""
        task_without_ctx = ConcreteServiceTask(self.service_factory, None)
        stats = task_without_ctx.get_statistics()
        
        self.assertFalse(stats['has_service_context'])
        # 不应该包含队列相关的统计信息键
        self.assertNotIn('request_queue_available', stats)
        self.assertNotIn('response_queues_count', stats)
    
    def test_cleanup_without_queue_management(self):
        """测试清理过程不涉及队列管理"""
        # 启动服务
        self.service_task.start_running()
        
        # 执行清理
        self.service_task.cleanup()
        
        # 验证服务实例被清理
        self.assertTrue(self.service_task.service_instance.cleanup_called)
        self.assertFalse(self.service_task.is_running)
        
        # 队列应该仍然可用（由ServiceContext管理）
        self.assertIsNotNone(self.service_task.request_queue)
        self.assertIsNotNone(self.service_task.get_response_queue("target_node"))
    
    def test_direct_response_queue_sending(self):
        """测试直接向响应队列对象发送响应"""
        response_data = {
            'request_id': 'direct_test',
            'result': 'test_result',
            'success': True,
            'timestamp': time.time()
        }
        
        # 直接发送响应到队列对象
        self.service_task._send_response_to_queue(self.response_queue, response_data)
        
        # 验证响应被发送
        self.assertFalse(self.response_queue.empty())
        received = self.response_queue.get_nowait()
        self.assertEqual(received['request_id'], 'direct_test')
        self.assertEqual(received['result'], 'test_result')


if __name__ == '__main__':
    unittest.main()
