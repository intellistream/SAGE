"""
Queue Descriptor 使用示例

演示如何使用统一的通信描述符系统
"""

from sage.runtime.communication.queue_descriptor import QueueDescriptor, resolve_descriptor
from sage.runtime.communication.tests.test_queue_descriptor import register_all_test_implementations


def main():
    """主函数 - 演示基本用法"""
    print("🚀 Queue Descriptor 使用示例")
    print("=" * 40)
    
    # 首先注册测试实现
    register_all_test_implementations()
    
    # 按照需求示例使用
    print("\n1. 按照需求示例使用:")
    desc = QueueDescriptor(queue_id="sink1", queue_type="shm", metadata={"shm_name": "shm_abc"})
    queue = resolve_descriptor(desc)
    queue.put("test")
    data = queue.get()
    print(f"   结果: {data}")
    
    # 使用工厂方法创建不同类型的队列
    print("\n2. 使用工厂方法创建队列:")
    
    # 本地队列
    local_desc = QueueDescriptor.create_local_queue("my_local", maxsize=100)
    local_queue = resolve_descriptor(local_desc)
    local_queue.put("Hello Local!")
    print(f"   本地队列: {local_queue.get()}")
    
    # Ray队列
    ray_desc = QueueDescriptor.create_ray_queue("my_ray", maxsize=50)
    ray_queue = resolve_descriptor(ray_desc)
    ray_queue.put("Hello Ray!")
    print(f"   Ray队列: {ray_queue.get()}")
    
    # RPC队列
    rpc_desc = QueueDescriptor.create_rpc_queue("localhost", 8080, "my_rpc")
    rpc_queue = resolve_descriptor(rpc_desc)
    rpc_queue.put("Hello RPC!")
    print(f"   RPC队列: {rpc_queue.get()}")
    
    # 序列化和传输
    print("\n3. 序列化和跨进程传输:")
    desc_json = local_desc.to_json()
    print(f"   序列化: {desc_json}")
    
    # 模拟跨进程传输
    received_desc = QueueDescriptor.from_json(desc_json)
    received_queue = resolve_descriptor(received_desc)
    received_queue.put("Cross-process data")
    print(f"   跨进程数据: {received_queue.get()}")
    
    print("\n✅ 示例完成！")


if __name__ == "__main__":
    main()
