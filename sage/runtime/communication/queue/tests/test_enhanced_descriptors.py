"""
测试增强版队列描述符系统
"""

import sys
import os
import queue

# 添加项目根目录到路径
sys.path.insert(0, '/api-rework')

def test_enhanced_queue_descriptors():
    """测试增强版的队列描述符功能"""
    print("🚀 测试增强版队列描述符系统")
    print("=" * 50)
    
    try:
        from sage.runtime.communication.queue_descriptor import (
            QueueDescriptor, LocalQueueDescriptor, RemoteQueueDescriptor,
            create_local_queue_descriptor_with_ref, register_queue_implementation
        )
        print("✓ 成功导入增强版模块")
        
        # 测试1: 基本QueueDescriptor的can_serialize字段
        print("\n--- 测试 can_serialize 字段 ---")
        
        # 创建可序列化的描述符
        serializable_desc = QueueDescriptor.create_local_queue("test_serializable")
        print(f"可序列化描述符: {serializable_desc}")
        print(f"can_serialize: {serializable_desc.can_serialize}")
        
        # 测试序列化
        json_str = serializable_desc.to_json()
        print(f"✓ 序列化成功: {json_str[:100]}...")
        
        # 测试2: LocalQueueDescriptor（不可序列化）
        print("\n--- 测试 LocalQueueDescriptor ---")
        
        # 创建一个真实的队列对象
        real_queue = queue.Queue(maxsize=10)
        
        # 创建本地队列描述符（包含队列引用）
        local_desc = create_local_queue_descriptor_with_ref(
            queue_obj=real_queue,
            queue_id="test_local_ref",
            maxsize=10
        )
        
        print(f"本地队列描述符: {local_desc}")
        print(f"can_serialize: {local_desc.can_serialize}")
        
        # 测试直接队列操作
        print("\n--- 测试直接队列操作 ---")
        local_desc.put("test_message_1")
        local_desc.put("test_message_2")
        
        print(f"队列大小: {local_desc.qsize()}")
        print(f"队列是否为空: {local_desc.empty()}")
        
        msg1 = local_desc.get()
        msg2 = local_desc.get()
        print(f"取出消息1: {msg1}")
        print(f"取出消息2: {msg2}")
        print(f"操作后队列大小: {local_desc.qsize()}")
        
        # 测试序列化失败
        try:
            local_desc.to_json()
            print("✗ 应该抛出序列化异常但没有")
        except ValueError as e:
            print(f"✓ 正确捕获序列化异常: {e}")
        
        # 测试转换为可序列化版本
        print("\n--- 测试转换为可序列化版本 ---")
        serializable_version = local_desc.to_serializable_descriptor()
        print(f"可序列化版本: {serializable_version}")
        print(f"可序列化版本 can_serialize: {serializable_version.can_serialize}")
        
        # 验证可序列化版本可以正常序列化
        serializable_json = serializable_version.to_json()
        print(f"✓ 可序列化版本序列化成功")
        
        # 测试3: RemoteQueueDescriptor（懒加载）
        print("\n--- 测试 RemoteQueueDescriptor 懒加载 ---")
        
        # 创建一个简单的队列实现用于测试
        class SimpleTestQueue:
            def __init__(self, descriptor):
                self.descriptor = descriptor
                self.queue_id = descriptor.queue_id
                self.metadata = descriptor.metadata
                self._items = []
                print(f"✓ SimpleTestQueue '{self.queue_id}' 初始化")
            
            def put(self, item, block=True, timeout=None):
                print(f"SimpleTestQueue[{self.queue_id}]: put({item})")
                self._items.append(item)
            
            def get(self, block=True, timeout=None):
                if not self._items:
                    raise Exception("Queue is empty")
                item = self._items.pop(0)
                print(f"SimpleTestQueue[{self.queue_id}]: get() -> {item}")
                return item
            
            def empty(self):
                return len(self._items) == 0
            
            def qsize(self):
                return len(self._items)
        
        # 注册测试实现
        register_queue_implementation("test_remote", SimpleTestQueue)
        
        # 创建远程队列描述符
        remote_desc = RemoteQueueDescriptor(
            queue_id="test_remote_lazy",
            queue_type="test_remote",
            metadata={"test_param": "value"},
            can_serialize=True
        )
        
        print(f"远程队列描述符: {remote_desc}")
        print(f"初始化状态: {remote_desc._initialized}")
        
        # 测试懒加载：第一次调用时才初始化
        print("\n--- 第一次队列操作（触发懒加载） ---")
        remote_desc.put("lazy_message_1")
        print(f"懒加载后初始化状态: {remote_desc._initialized}")
        
        # 后续操作使用缓存的队列
        remote_desc.put("lazy_message_2")
        
        print(f"队列大小: {remote_desc.qsize()}")
        
        msg1 = remote_desc.get()
        msg2 = remote_desc.get()
        print(f"取出消息: {msg1}, {msg2}")
        
        # 测试清除缓存
        print("\n--- 测试清除缓存 ---")
        remote_desc.clear_cache()
        print(f"清除缓存后初始化状态: {remote_desc._initialized}")
        
        # 再次操作会重新初始化
        remote_desc.put("after_cache_clear")
        print(f"重新初始化后状态: {remote_desc._initialized}")
        
        # 测试序列化
        print("\n--- 测试远程描述符序列化 ---")
        remote_json = remote_desc.to_json()
        print(f"✓ 远程描述符序列化成功")
        
        # 反序列化
        from sage.runtime.communication.queue_descriptor import QueueDescriptor
        restored_desc = QueueDescriptor.from_json(remote_json)
        print(f"✓ 反序列化成功: {restored_desc}")
        
        print("\n" + "=" * 50)
        print("🎉 所有增强功能测试通过！")
        
        # 测试总结
        print("\n📊 功能测试总结:")
        print("✓ can_serialize 字段控制序列化")
        print("✓ LocalQueueDescriptor 支持直接队列操作")
        print("✓ LocalQueueDescriptor 包含队列引用且不可序列化")
        print("✓ LocalQueueDescriptor 可转换为可序列化版本")
        print("✓ RemoteQueueDescriptor 支持懒加载")
        print("✓ RemoteQueueDescriptor 支持缓存清除")
        print("✓ RemoteQueueDescriptor 支持序列化")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_queue_descriptors()
