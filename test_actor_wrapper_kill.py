#!/usr/bin/env python3
"""
测试ActorWrapper的kill功能
"""
import time
import ray
import subprocess
from sage_utils.ray_init_helper import ensure_ray_initialized
from sage_utils.actor_wrapper import ActorWrapper

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
        time.sleep(1)  # 模拟一些清理工作
        return f"Cleanup done by {self.name}"

def test_actor_wrapper_kill():
    print("=== ActorWrapper Kill Test ===")
    
    # 1. 确保Ray初始化
    print("1. Initializing Ray...")
    ensure_ray_initialized()
    
    # 2. 创建带名字的Actor
    print("\n2. Creating named actor...")
    actor_name = "test_wrapper_actor_456"
    
    # 创建Ray Actor
    ray_actor = TestActor.options(name=actor_name, lifetime="detached").remote("TestWrapperActor456")
    
    # 用ActorWrapper包装
    wrapped_actor = ActorWrapper(ray_actor)
    
    print(f"Created and wrapped actor: {wrapped_actor}")
    print(f"Is Ray Actor: {wrapped_actor.is_ray_actor()}")
    print(f"Is Local: {wrapped_actor.is_local()}")
    
    # 3. 测试wrapped actor功能
    print("\n3. Testing wrapped actor functionality...")
    name_result = wrapped_actor.get_name()
    print(f"Actor name: {name_result}")
    
    work_result = wrapped_actor.do_work()
    print(f"Work result: {work_result}")
    
    # 4. 查看当前的actors
    print("\n4. Listing actors before kill...")
    result = subprocess.run(["ray", "list", "actors"], capture_output=True, text=True)
    print("Current actors:")
    print(result.stdout)
    
    # 5. 测试只kill（不cleanup）
    print("\n5. Testing kill_actor method...")
    kill_success = wrapped_actor.kill_actor()
    print(f"Kill success: {kill_success}")
    
    # 等待一下
    time.sleep(2)
    
    print("\n6. Listing actors after kill...")
    result = subprocess.run(["ray", "list", "actors"], capture_output=True, text=True)
    print("Actors after kill:")
    print(result.stdout)
    
    # 7. 验证actor是否真的被kill了
    print("\n7. Verifying actor is killed...")
    try:
        result = wrapped_actor.get_name()
        print(f"✗ Actor still alive, got: {result}")
    except Exception as e:
        print(f"✓ Actor successfully killed: {e}")

def test_actor_wrapper_cleanup_and_kill():
    print("\n\n=== ActorWrapper Cleanup and Kill Test ===")
    
    # 1. 创建新的Actor进行cleanup测试
    print("1. Creating another actor for cleanup test...")
    actor_name2 = "test_cleanup_actor_789"
    
    ray_actor2 = TestActor.options(name=actor_name2, lifetime="detached").remote("TestCleanupActor789")
    wrapped_actor2 = ActorWrapper(ray_actor2)
    
    print(f"Created wrapped actor: {wrapped_actor2}")
    
    # 2. 测试功能
    print("\n2. Testing actor functionality...")
    name_result = wrapped_actor2.get_name()
    print(f"Actor name: {name_result}")
    
    # 3. 查看actors
    print("\n3. Listing actors before cleanup_and_kill...")
    result = subprocess.run(["ray", "list", "actors"], capture_output=True, text=True)
    print("Current actors:")
    print(result.stdout)
    
    # 4. 测试cleanup_and_kill方法
    print("\n4. Testing cleanup_and_kill method...")
    cleanup_success, kill_success = wrapped_actor2.cleanup_and_kill(cleanup_timeout=3.0)
    print(f"Cleanup success: {cleanup_success}")
    print(f"Kill success: {kill_success}")
    
    # 等待一下
    time.sleep(2)
    
    print("\n5. Listing actors after cleanup_and_kill...")
    result = subprocess.run(["ray", "list", "actors"], capture_output=True, text=True)
    print("Actors after cleanup_and_kill:")
    print(result.stdout)
    
    # 6. 验证actor是否被kill了
    print("\n6. Verifying actor is killed...")
    try:
        result = wrapped_actor2.get_name()
        print(f"✗ Actor still alive, got: {result}")
    except Exception as e:
        print(f"✓ Actor successfully killed: {e}")

def test_local_object_wrapper():
    print("\n\n=== Local Object Wrapper Test ===")
    
    # 创建本地对象并包装
    class LocalTestObject:
        def __init__(self, name):
            self.name = name
        
        def get_name(self):
            return self.name
        
        def cleanup(self):
            print(f"Local object {self.name} cleanup called")
            return f"Local cleanup done by {self.name}"
    
    local_obj = LocalTestObject("LocalTest")
    wrapped_local = ActorWrapper(local_obj)
    
    print(f"Created wrapped local object: {wrapped_local}")
    print(f"Is Ray Actor: {wrapped_local.is_ray_actor()}")
    print(f"Is Local: {wrapped_local.is_local()}")
    
    # 测试本地对象的kill方法（应该返回False）
    kill_success = wrapped_local.kill_actor()
    print(f"Kill local object success (should be False): {kill_success}")
    
    cleanup_success, kill_success = wrapped_local.cleanup_and_kill()
    print(f"Cleanup and kill local object - cleanup: {cleanup_success}, kill: {kill_success}")

def main():
    try:
        test_actor_wrapper_kill()
        test_actor_wrapper_cleanup_and_kill()
        test_local_object_wrapper()
        print("\n=== All Tests Complete ===")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
