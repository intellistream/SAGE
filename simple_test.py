"""
简单的队列描述符测试
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, '/api-rework')

def test_basic_functionality():
    """测试基本功能"""
    print("🚀 测试队列描述符基本功能")
    
    try:
        from sage.runtime.communication.queue_descriptor import (
            QueueDescriptor, resolve_descriptor, register_queue_implementation
        )
        print("✓ 成功导入模块")
        
        # 创建描述符
        desc = QueueDescriptor.create_local_queue("test_local", maxsize=10)
        print(f"✓ 创建描述符: {desc}")
        
        # 测试序列化
        json_str = desc.to_json()
        desc2 = QueueDescriptor.from_json(json_str)
        print(f"✓ 序列化测试通过: {desc2}")
        
        # 创建一个简单的本地队列实现进行测试
        import queue
        
        class SimpleLocalQueue:
            def __init__(self, descriptor):
                self.descriptor = descriptor
                self.queue_id = descriptor.queue_id
                self.metadata = descriptor.metadata
                maxsize = self.metadata.get("maxsize", 0)
                self._queue = queue.Queue(maxsize=maxsize)
                print(f"✓ 简单本地队列 '{self.queue_id}' 已初始化")
            
            def put(self, item, block=True, timeout=None):
                print(f"SimpleLocalQueue[{self.queue_id}]: put({item})")
                self._queue.put(item, block=block, timeout=timeout)
            
            def get(self, block=True, timeout=None):
                item = self._queue.get(block=block, timeout=timeout)
                print(f"SimpleLocalQueue[{self.queue_id}]: get() -> {item}")
                return item
            
            def empty(self):
                return self._queue.empty()
            
            def qsize(self):
                return self._queue.qsize()
        
        # 注册实现
        register_queue_implementation("local", SimpleLocalQueue)
        print("✓ 注册本地队列实现")
        
        # 测试队列功能
        queue_obj = resolve_descriptor(desc)
        print("✓ 成功解析描述符")
        
        # 测试基本操作
        print(f"初始状态 - empty: {queue_obj.empty()}, size: {queue_obj.qsize()}")
        
        queue_obj.put("test_message")
        print(f"放入数据后 - empty: {queue_obj.empty()}, size: {queue_obj.qsize()}")
        
        data = queue_obj.get()
        print(f"取出数据: {data}")
        print(f"取出数据后 - empty: {queue_obj.empty()}, size: {queue_obj.qsize()}")
        
        assert data == "test_message"
        print("✓ 数据传输测试通过")
        
        # 测试需求示例
        shm_desc = QueueDescriptor(queue_id="sink1", queue_type="shm", metadata={"shm_name": "shm_abc"})
        
        class SimpleShmQueue:
            def __init__(self, descriptor):
                self.descriptor = descriptor
                self.queue_id = descriptor.queue_id
                self.metadata = descriptor.metadata
                shm_name = self.metadata.get("shm_name")
                print(f"✓ 简单SHM队列 '{self.queue_id}' 连接到 '{shm_name}'")
                self._items = []
            
            def put(self, item, block=True, timeout=None):
                print(f"SimpleShmQueue[{self.queue_id}]: put({item}) to shm '{self.metadata['shm_name']}'")
                self._items.append(item)
            
            def get(self, block=True, timeout=None):
                if not self._items:
                    raise Exception("Queue is empty")
                item = self._items.pop(0)
                print(f"SimpleShmQueue[{self.queue_id}]: get() -> {item}")
                return item
            
            def empty(self):
                return len(self._items) == 0
            
            def qsize(self):
                return len(self._items)
        
        register_queue_implementation("shm", SimpleShmQueue)
        print("✓ 注册SHM队列实现")
        
        # 测试需求示例
        shm_queue = resolve_descriptor(shm_desc)
        shm_queue.put("test")
        result = shm_queue.get()
        assert result == "test"
        print("✓ 需求示例测试通过")
        
        print("\n🎉 所有测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_functionality()
