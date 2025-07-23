#!/usr/bin/env python3
"""
测试Ray Actor的创建和kill操作
"""
import time
import ray
from sage_utils.ray_init_helper import ensure_ray_initialized

@ray.remote
class TestActor:
    def __init__(self, name):
        self.name = name
        print(f"TestActor {name} initialized")
    
    def get_name(self):
        return self.name
    
    def do_work(self):
        print(f"TestActor {self.name} is working...")
        return f"Work done by {self.name}"
    
    def cleanup(self):
        print(f"TestActor {self.name} cleanup called")
        return f"Cleanup done by {self.name}"

def main():
    print("=== Ray Actor Kill Test ===")
    
    # 1. 确保Ray初始化
    print("1. Initializing Ray...")
    ensure_ray_initialized()
    
    # 2. 创建带名字的Actor
    print("\n2. Creating named actor...")
    actor_name = "test_actor_123"
    
    # 创建带名字的actor
    test_actor = TestActor.options(name=actor_name, lifetime="detached").remote("TestActor123")
    
    print(f"Created actor with name: {actor_name}")
    
    # 3. 测试actor功能
    print("\n3. Testing actor functionality...")
    name_result = ray.get(test_actor.get_name.remote())
    print(f"Actor name: {name_result}")
    
    work_result = ray.get(test_actor.do_work.remote())
    print(f"Work result: {work_result}")
    
    # 4. 查看当前的actors
    print("\n4. Listing actors before kill...")
    import subprocess
    result = subprocess.run(["ray", "list", "actors"], capture_output=True, text=True)
    print("Current actors:")
    print(result.stdout)
    
    # 5. 尝试调用cleanup方法
    print("\n5. Calling cleanup method...")
    try:
        cleanup_result = ray.get(test_actor.cleanup.remote())
        print(f"Cleanup result: {cleanup_result}")
    except Exception as e:
        print(f"Cleanup failed: {e}")
    
    # 6. 尝试kill actor
    print("\n6. Attempting to kill actor...")
    try:
        # 方法1：使用ray.kill直接kill actor handle
        print("Method 1: ray.kill(actor_handle)")
        ray.kill(test_actor)
        print("✓ ray.kill(actor_handle) succeeded")
    except Exception as e:
        print(f"✗ Method 1 failed: {e}")
        
        # 方法2：通过名字获取actor并kill
        try:
            print("Method 2: ray.kill(ray.get_actor(name))")
            named_actor = ray.get_actor(actor_name)
            ray.kill(named_actor)
            print("✓ ray.kill(named_actor) succeeded")
        except Exception as e2:
            print(f"✗ Method 2 failed: {e2}")
    
    # 7. 等待一下，然后再次查看actors
    print("\n7. Waiting 3 seconds...")
    time.sleep(3)
    
    print("8. Listing actors after kill...")
    result = subprocess.run(["ray", "list", "actors"], capture_output=True, text=True)
    print("Actors after kill:")
    print(result.stdout)
    
    # 9. 验证actor是否真的被kill了
    print("\n9. Verifying actor is killed...")
    try:
        # 尝试调用已kill的actor
        result = ray.get(test_actor.get_name.remote())
        print(f"✗ Actor still alive, got: {result}")
    except Exception as e:
        print(f"✓ Actor successfully killed: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
