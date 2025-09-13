#!/usr/bin/env python3
"""
简化的Ray Actor测试
专门用于验证修复后的Ray队列功能
"""

import sys
import os
import time

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "packages/sage-kernel/src"))

def test_ray_queue_basic():
    """测试基本的Ray队列功能"""
    print("测试Ray队列基本功能...")
    
    try:
        from sage.kernel.runtime.communication.queue_descriptor import RayQueueDescriptor
        from sage.kernel.utils.ray.ray import ensure_ray_initialized
        import ray
        
        # 初始化Ray
        ensure_ray_initialized()
        
        # 创建队列描述符
        descriptor = RayQueueDescriptor(maxsize=100, queue_id='test_basic')
        print(f"✓ 创建队列描述符: {descriptor.queue_id}")
        
        # 序列化和反序列化
        data = descriptor.to_dict()
        new_descriptor = RayQueueDescriptor.from_dict(data)
        print(f"✓ 序列化和反序列化成功, maxsize类型: {type(new_descriptor.maxsize)}")
        
        # 获取队列实例
        queue = new_descriptor.queue_instance
        print(f"✓ 获取队列实例: {type(queue)}")
        
        # 基本操作
        queue.put("test_item_1")
        queue.put("test_item_2")
        
        item1 = queue.get(timeout=1)
        item2 = queue.get(timeout=1)
        
        print(f"✓ 队列操作成功: {item1}, {item2}")
        
        return True
        
    except Exception as e:
        print(f"✗ 基本测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            ray.shutdown()
        except:
            pass

def test_ray_actor_simple():
    """测试简单的Ray Actor"""
    print("测试简单的Ray Actor...")
    
    try:
        import ray
        from sage.kernel.runtime.communication.queue_descriptor import RayQueueDescriptor
        from sage.kernel.utils.ray.ray import ensure_ray_initialized
        
        # 初始化Ray
        ensure_ray_initialized()
        
        @ray.remote
        class SimpleActor:
            def __init__(self):
                self.count = 0
                
            def process_queue(self, queue_dict):
                try:
                    from sage.kernel.runtime.communication.queue_descriptor import resolve_descriptor
                    descriptor = resolve_descriptor(queue_dict)
                    queue = descriptor.queue_instance
                    
                    # 放入一个项目
                    queue.put(f"actor_item_{self.count}")
                    self.count += 1
                    
                    return f"Success: put item {self.count}"
                except Exception as e:
                    return f"Error: {e}"
        
        # 创建队列和Actor
        descriptor = RayQueueDescriptor(maxsize=100, queue_id='test_actor')
        queue_dict = descriptor.to_dict()
        
        actor = SimpleActor.remote()
        
        # 测试Actor操作
        result = ray.get(actor.process_queue.remote(queue_dict))
        print(f"✓ Actor操作结果: {result}")
        
        # 验证队列中的项目
        queue = descriptor.queue_instance
        item = queue.get(timeout=2)
        print(f"✓ 从队列获取Actor放入的项目: {item}")
        
        return True
        
    except Exception as e:
        print(f"✗ Actor测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            ray.shutdown()
        except:
            pass

def main():
    """主测试函数"""
    print("开始简化的Ray测试...")
    
    results = {}
    
    # 测试1：基本功能
    results['basic'] = test_ray_queue_basic()
    time.sleep(1)
    
    # 测试2：简单Actor
    results['actor'] = test_ray_actor_simple()
    
    # 总结
    print("\n" + "="*50)
    print("测试总结:")
    print("="*50)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {test_name}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)