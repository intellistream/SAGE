#!/usr/bin/env python3
"""
测试修复后的Dispatcher cleanup功能
"""
import ray
import time
from sage_utils.ray_init_helper import ensure_ray_initialized
from sage_utils.actor_wrapper import ActorWrapper
from sage_runtime.dispatcher import Dispatcher

@ray.remote
class TestTask:
    def __init__(self, name):
        self.name = name
        self.processed_count = 0
        print(f"TestTask {name} initialized")
    
    def process(self, data):
        self.processed_count += 1
        print(f"TestTask {self.name} processing: {data} (count: {self.processed_count})")
        time.sleep(0.1)  # 模拟处理时间
        return f"Processed {data} by {self.name}"
    
    def get_status(self):
        return {
            "name": self.name,
            "processed_count": self.processed_count
        }
    
    def cleanup(self):
        print(f"TestTask {self.name} cleanup called")
        return f"Cleanup done by {self.name}"

def main():
    print("=== Dispatcher Cleanup Test ===")
    
    # 1. 初始化Ray
    print("1. Initializing Ray...")
    ensure_ray_initialized()
    
    # 2. 创建Dispatcher
    print("\n2. Creating Dispatcher...")
    dispatcher = Dispatcher("test_dispatcher")
    
    # 3. 添加一些Ray Actor任务
    print("\n3. Adding Ray Actor tasks...")
    task_configs = [
        {"name": "task1", "actor_name": "test_task_1"},
        {"name": "task2", "actor_name": "test_task_2"},
        {"name": "task3", "actor_name": "test_task_3"},
    ]
    
    for config in task_configs:
        # 创建Ray Actor
        ray_actor = TestTask.options(
            name=config["actor_name"],
            lifetime="detached"
        ).remote(config["name"])
        
        # 包装成ActorWrapper
        actor_wrapper = ActorWrapper(ray_actor)
        
        # 添加到dispatcher
        dispatcher.tasks[config["name"]] = actor_wrapper
        print(f"Added task: {config['name']}")
    
    # 4. 测试任务功能
    print("\n4. Testing task functionality...")
    for i, (task_name, actor_wrapper) in enumerate(dispatcher.tasks.items()):
        try:
            result = actor_wrapper.process(f"data_{i}")
            print(f"Task {task_name} result: {result}")
        except Exception as e:
            print(f"Task {task_name} failed: {e}")
    
    # 5. 查看当前的actors
    print("\n5. Current Ray actors before cleanup:")
    import subprocess
    result = subprocess.run(["ray", "list", "actors"], capture_output=True, text=True)
    print(result.stdout)
    
    # 6. 测试cleanup功能
    print("\n6. Testing dispatcher cleanup...")
    try:
        dispatcher._cleanup_ray_actors()
        print("✓ Dispatcher cleanup completed successfully")
    except Exception as e:
        print(f"✗ Dispatcher cleanup failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 7. 等待一下，然后检查actors是否被清理
    print("\n7. Waiting 3 seconds...")
    time.sleep(3)
    
    print("8. Ray actors after cleanup:")
    result = subprocess.run(["ray", "list", "actors"], capture_output=True, text=True)
    print(result.stdout)
    
    # 9. 验证任务是否真的被kill了
    print("\n9. Verifying tasks are killed...")
    for task_name, actor_wrapper in dispatcher.tasks.items():
        try:
            result = actor_wrapper.get_status()
            print(f"✗ Task {task_name} still alive: {result}")
        except Exception as e:
            print(f"✓ Task {task_name} successfully killed: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
