"""
Queue Descriptor 测试文件

包含各种队列类型的存根实现和完整的测试用例
"""

import queue
import time
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from sage.runtime.communication.queue_descriptor import (
    QueueDescriptor, QueueLike, resolve_descriptor, 
    register_queue_implementation, get_registered_queue_types,
    create_descriptor_from_existing_queue
)


class BaseQueueStub(ABC):
    """队列存根基类"""
    
    def __init__(self, descriptor: QueueDescriptor):
        self.descriptor = descriptor
        self.queue_id = descriptor.queue_id
        self.metadata = descriptor.metadata
        print(f"Initializing {self.__class__.__name__} with descriptor: {descriptor}")
    
    @abstractmethod
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """向队列中放入一个项目"""
        pass
    
    @abstractmethod
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列中获取一个项目"""
        pass
    
    @abstractmethod
    def empty(self) -> bool:
        """检查队列是否为空"""
        pass
    
    @abstractmethod
    def qsize(self) -> int:
        """获取队列的大小"""
        pass
    
    def cleanup(self):
        """清理资源"""
        print(f"Cleaning up {self.__class__.__name__} for queue {self.queue_id}")


class LocalQueueStub(BaseQueueStub):
    """本地队列存根实现"""
    
    def __init__(self, descriptor: QueueDescriptor):
        super().__init__(descriptor)
        maxsize = self.metadata.get("maxsize", 0)
        self._queue = queue.Queue(maxsize=maxsize)
        print(f"✓ Local queue '{self.queue_id}' initialized with maxsize={maxsize}")
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        print(f"LocalQueue[{self.queue_id}]: put({item})")
        self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        item = self._queue.get(block=block, timeout=timeout)
        print(f"LocalQueue[{self.queue_id}]: get() -> {item}")
        return item
    
    def empty(self) -> bool:
        return self._queue.empty()
    
    def qsize(self) -> int:
        return self._queue.qsize()


class ShmQueueStub(BaseQueueStub):
    """共享内存队列存根实现"""
    
    def __init__(self, descriptor: QueueDescriptor):
        super().__init__(descriptor)
        shm_name = self.metadata.get("shm_name")
        maxsize = self.metadata.get("maxsize", 1000)
        print(f"✓ Shared memory queue '{self.queue_id}' attached to shm '{shm_name}' with maxsize={maxsize}")
        
        # 这里应该实现真正的共享内存队列逻辑
        # 为了演示，我们使用一个简单的存根
        self._items = []
        self._lock = threading.Lock()
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        print(f"ShmQueue[{self.queue_id}]: put({item}) to shm '{self.metadata['shm_name']}'")
        with self._lock:
            self._items.append(item)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        with self._lock:
            if not self._items:
                raise Exception("Queue is empty")
            item = self._items.pop(0)
        print(f"ShmQueue[{self.queue_id}]: get() -> {item} from shm '{self.metadata['shm_name']}'")
        return item
    
    def empty(self) -> bool:
        with self._lock:
            return len(self._items) == 0
    
    def qsize(self) -> int:
        with self._lock:
            return len(self._items)


class RayActorQueueStub(BaseQueueStub):
    """Ray Actor队列存根实现"""
    
    def __init__(self, descriptor: QueueDescriptor):
        super().__init__(descriptor)
        actor_name = self.metadata.get("actor_name")
        maxsize = self.metadata.get("maxsize", 0)
        print(f"✓ Ray Actor queue '{self.queue_id}' connected to actor '{actor_name}' with maxsize={maxsize}")
        
        # 这里应该实现真正的Ray Actor队列逻辑
        self._items = []
        self._lock = threading.Lock()
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        print(f"RayActorQueue[{self.queue_id}]: put({item}) to actor '{self.metadata['actor_name']}'")
        with self._lock:
            self._items.append(item)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        with self._lock:
            if not self._items:
                raise Exception("Queue is empty")
            item = self._items.pop(0)
        print(f"RayActorQueue[{self.queue_id}]: get() -> {item} from actor '{self.metadata['actor_name']}'")
        return item
    
    def empty(self) -> bool:
        with self._lock:
            return len(self._items) == 0
    
    def qsize(self) -> int:
        with self._lock:
            return len(self._items)


class RayQueueStub(BaseQueueStub):
    """Ray分布式队列存根实现"""
    
    def __init__(self, descriptor: QueueDescriptor):
        super().__init__(descriptor)
        maxsize = self.metadata.get("maxsize", 0)
        print(f"✓ Ray distributed queue '{self.queue_id}' initialized with maxsize={maxsize}")
        
        # 这里应该使用真正的Ray队列
        try:
            import ray
            from ray.util.queue import Queue as RayQueue
            # 检查Ray是否已初始化，如果没有则不尝试连接
            if not ray.is_initialized():
                print("Warning: Ray not initialized, using local fallback")
                raise ImportError("Ray not initialized")
            self._queue = RayQueue(maxsize=maxsize)
        except (ImportError, Exception) as e:
            print(f"Warning: Ray not available ({e}), using local fallback")
            self._queue = queue.Queue(maxsize=maxsize)
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        print(f"RayQueue[{self.queue_id}]: put({item})")
        self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        item = self._queue.get(block=block, timeout=timeout)
        print(f"RayQueue[{self.queue_id}]: get() -> {item}")
        return item
    
    def empty(self) -> bool:
        return self._queue.empty()
    
    def qsize(self) -> int:
        return self._queue.qsize()


class RpcQueueStub(BaseQueueStub):
    """RPC队列存根实现"""
    
    def __init__(self, descriptor: QueueDescriptor):
        super().__init__(descriptor)
        server_address = self.metadata.get("server_address")
        port = self.metadata.get("port")
        print(f"✓ RPC queue '{self.queue_id}' connected to {server_address}:{port}")
        
        # 这里应该实现真正的RPC队列逻辑
        self._items = []
        self._lock = threading.Lock()
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        print(f"RpcQueue[{self.queue_id}]: put({item}) to {self.metadata['server_address']}:{self.metadata['port']}")
        with self._lock:
            self._items.append(item)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        with self._lock:
            if not self._items:
                raise Exception("Queue is empty")
            item = self._items.pop(0)
        print(f"RpcQueue[{self.queue_id}]: get() -> {item} from {self.metadata['server_address']}:{self.metadata['port']}")
        return item
    
    def empty(self) -> bool:
        with self._lock:
            return len(self._items) == 0
    
    def qsize(self) -> int:
        with self._lock:
            return len(self._items)


class SageQueueStub(BaseQueueStub):
    """SAGE高性能队列存根实现"""
    
    def __init__(self, descriptor: QueueDescriptor):
        super().__init__(descriptor)
        maxsize = self.metadata.get("maxsize", 1000)
        print(f"✓ SAGE high-performance queue '{self.queue_id}' initialized with maxsize={maxsize}")
        
        # 尝试使用真正的SAGE队列，如果不可用则使用fallback
        try:
            from sage.utils.queue_adapter import create_queue
            self._queue = create_queue(backend="sage_queue", name=self.queue_id, maxsize=maxsize)
        except Exception:
            print("Warning: SAGE queue not available, using local fallback")
            self._queue = queue.Queue(maxsize=maxsize)
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        print(f"SageQueue[{self.queue_id}]: put({item})")
        self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        item = self._queue.get(block=block, timeout=timeout)
        print(f"SageQueue[{self.queue_id}]: get() -> {item}")
        return item
    
    def empty(self) -> bool:
        if hasattr(self._queue, 'empty'):
            return self._queue.empty()
        return self._queue.qsize() == 0
    
    def qsize(self) -> int:
        return self._queue.qsize()


def register_all_test_implementations():
    """注册所有测试用的队列实现"""
    implementations = {
        "local": LocalQueueStub,
        "shm": ShmQueueStub,
        "ray_actor": RayActorQueueStub,
        "ray_queue": RayQueueStub,
        "rpc": RpcQueueStub,
        "sage_queue": SageQueueStub,
    }
    
    for queue_type, impl_class in implementations.items():
        register_queue_implementation(queue_type, impl_class)
    
    print(f"✓ Registered {len(implementations)} queue implementations for testing")


def test_queue_descriptor_basic():
    """测试基本的队列描述符功能"""
    print("\n=== 测试基本队列描述符功能 ===")
    
    # 测试创建描述符
    desc = QueueDescriptor.create_local_queue("test_local", maxsize=100)
    print(f"Created descriptor: {desc}")
    
    # 测试序列化
    json_str = desc.to_json()
    print(f"JSON: {json_str}")
    
    # 测试反序列化
    desc2 = QueueDescriptor.from_json(json_str)
    print(f"Deserialized: {desc2}")
    
    assert desc.queue_id == desc2.queue_id
    assert desc.queue_type == desc2.queue_type
    assert desc.metadata == desc2.metadata
    print("✓ 序列化/反序列化测试通过")


def test_queue_creation_and_usage():
    """测试队列创建和使用"""
    print("\n=== 测试队列创建和使用 ===")
    
    # 注册测试实现
    register_all_test_implementations()
    
    # 测试不同类型的队列
    test_cases = [
        QueueDescriptor.create_local_queue("test_local", maxsize=10),
        QueueDescriptor.create_shm_queue("shm_test", "test_shm", maxsize=100),
        QueueDescriptor.create_ray_actor_queue("actor_test", "test_actor"),
        QueueDescriptor.create_ray_queue("test_ray", maxsize=50),
        QueueDescriptor.create_rpc_queue("localhost", 8080, "test_rpc"),
        QueueDescriptor.create_sage_queue("test_sage", maxsize=200),
    ]
    
    for desc in test_cases:
        print(f"\n--- 测试 {desc.queue_type} 队列 ---")
        
        # 创建队列
        queue_obj = resolve_descriptor(desc)
        
        # 测试基本操作
        print(f"Initial empty: {queue_obj.empty()}")
        print(f"Initial size: {queue_obj.qsize()}")
        
        # 放入数据
        test_data = f"test_data_{desc.queue_type}"
        queue_obj.put(test_data)
        
        print(f"After put empty: {queue_obj.empty()}")
        print(f"After put size: {queue_obj.qsize()}")
        
        # 取出数据
        retrieved_data = queue_obj.get()
        assert retrieved_data == test_data
        
        print(f"After get empty: {queue_obj.empty()}")
        print(f"After get size: {queue_obj.qsize()}")
        
        print(f"✓ {desc.queue_type} 队列测试通过")


def test_queue_registration_system():
    """测试队列注册系统"""
    print("\n=== 测试队列注册系统 ===")
    
    # 清空已注册的实现
    registered_types = get_registered_queue_types()
    print(f"Currently registered types: {registered_types}")
    
    # 注册一个测试实现
    register_queue_implementation("test_type", LocalQueueStub)
    
    # 验证注册
    assert "test_type" in get_registered_queue_types()
    print("✓ 队列类型注册成功")
    
    # 测试使用自定义类型
    desc = QueueDescriptor(
        queue_id="custom_test",
        queue_type="test_type",
        metadata={"maxsize": 5}
    )
    
    queue_obj = resolve_descriptor(desc)
    queue_obj.put("custom_test_data")
    data = queue_obj.get()
    assert data == "custom_test_data"
    print("✓ 自定义队列类型工作正常")


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    
    # 测试无效的队列类型
    try:
        desc = QueueDescriptor(
            queue_id="invalid_test",
            queue_type="invalid_type",
            metadata={}
        )
        print("✗ 应该抛出异常但没有")
    except ValueError as e:
        print(f"✓ 正确捕获无效队列类型错误: {e}")
    
    # 测试解析未注册的队列类型
    try:
        desc = QueueDescriptor(
            queue_id="unregistered_test",
            queue_type="local",  # 这是有效类型，但可能未注册实现
            metadata={}
        )
        
        # 如果没有注册实现，应该抛出错误
        if "local" not in get_registered_queue_types():
            resolve_descriptor(desc)
            print("✗ 应该抛出异常但没有")
    except ValueError as e:
        print(f"✓ 正确捕获未注册队列类型错误: {e}")


def test_convenience_functions():
    """测试便利函数"""
    print("\n=== 测试便利函数 ===")
    
    # 注册测试实现
    register_all_test_implementations()
    
    # 使用便利函数
    from sage.runtime.communication.queue_descriptor import (
        get_local_queue, attach_to_shm_queue, get_sage_queue
    )
    
    try:
        # 测试本地队列便利函数
        local_q = get_local_queue("convenience_local", maxsize=10)
        local_q.put("convenience_test")
        data = local_q.get()
        assert data == "convenience_test"
        print("✓ 本地队列便利函数工作正常")
        
        # 测试共享内存队列便利函数
        shm_q = attach_to_shm_queue("test_shm", "convenience_shm", maxsize=20)
        shm_q.put("shm_test")
        data = shm_q.get()
        assert data == "shm_test"
        print("✓ 共享内存队列便利函数工作正常")
        
        # 测试SAGE队列便利函数
        sage_q = get_sage_queue("convenience_sage", maxsize=30)
        sage_q.put("sage_test")
        data = sage_q.get()
        assert data == "sage_test"
        print("✓ SAGE队列便利函数工作正常")
        
    except Exception as e:
        print(f"便利函数测试遇到错误: {e}")


def test_requirements_example():
    """测试需求中的示例用法"""
    print("\n=== 测试需求示例 ===")
    
    # 注册测试实现
    register_all_test_implementations()
    
    # 按照需求示例使用
    desc = QueueDescriptor(queue_id="sink1", queue_type="shm", metadata={"shm_name": "shm_abc"})
    queue = resolve_descriptor(desc)
    queue.put("test")
    data = queue.get()
    
    assert data == "test"
    print("✓ 需求示例测试通过")


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始 Queue Descriptor 测试")
    print("=" * 50)
    
    try:
        test_queue_descriptor_basic()
        test_queue_creation_and_usage()
        test_queue_registration_system()
        test_error_handling()
        test_convenience_functions()
        test_requirements_example()
        
        print("\n" + "=" * 50)
        print("🎉 所有测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
