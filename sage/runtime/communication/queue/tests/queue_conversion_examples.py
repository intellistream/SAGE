"""
Queue Conversion Examples - 队列转换示例

展示 SAGE Queue、Ray Queue 和 Queue Descriptor 之间的转换方法
"""

import logging
import time
from typing import Any, Optional

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_sage_queue_conversion():
    """
    演示 SAGE Queue 与 Queue Descriptor 的转换
    """
    print("\n=== SAGE Queue 转换示例 ===")
    
    try:
        # 方法1: 通过 QueueDescriptor 创建 SAGE Queue
        from sage.runtime.communication.queue_descriptor import QueueDescriptor, resolve_descriptor
        
        # 创建描述符
        descriptor = QueueDescriptor.create_sage_queue(
            queue_id="test_sage_queue",
            maxsize=1024 * 1024,
            auto_cleanup=True,
            namespace="test",
            enable_multi_tenant=True
        )
        
        print(f"创建的描述符: {descriptor}")
        
        # 从描述符创建队列
        sage_queue_stub = resolve_descriptor(descriptor)
        print(f"从描述符创建的队列: {sage_queue_stub}")
        
        # 测试队列操作
        sage_queue_stub.put("Hello SAGE Queue!")
        item = sage_queue_stub.get()
        print(f"队列操作测试: 放入和取出 '{item}'")
        
        # 获取队列统计信息
        stats = sage_queue_stub.get_stats()
        print(f"队列统计信息: {stats}")
        
        # 将队列转换回描述符
        converted_descriptor = sage_queue_stub.to_descriptor()
        print(f"转换回的描述符: {converted_descriptor}")
        
        # 验证描述符序列化
        json_str = converted_descriptor.to_json()
        print(f"序列化的描述符: {json_str[:100]}...")
        
        # 从JSON恢复描述符
        restored_descriptor = QueueDescriptor.from_json(json_str)
        print(f"恢复的描述符: {restored_descriptor}")
        
        sage_queue_stub.close()
        
    except Exception as e:
        print(f"SAGE Queue 示例失败: {e}")
        logger.exception("SAGE Queue example failed")


def example_ray_queue_conversion():
    """
    演示 Ray Queue 与 Queue Descriptor 的转换
    """
    print("\n=== Ray Queue 转换示例 ===")
    
    try:
        # 初始化 Ray (如果还没有初始化)
        import ray
        if not ray.is_initialized():
            ray.init(local_mode=True)
            print("Ray 已初始化")
        
        from sage.runtime.communication.queue_descriptor import QueueDescriptor, resolve_descriptor
        
        # 方法1: Ray 原生分布式队列
        print("\n--- Ray 原生队列示例 ---")
        ray_descriptor = QueueDescriptor.create_ray_queue(
            queue_id="test_ray_queue",
            maxsize=100
        )
        
        print(f"Ray 队列描述符: {ray_descriptor}")
        
        ray_queue_stub = resolve_descriptor(ray_descriptor)
        print(f"Ray 队列 Stub: {ray_queue_stub}")
        
        # 测试操作
        ray_queue_stub.put("Hello Ray Queue!")
        item = ray_queue_stub.get()
        print(f"Ray 队列操作测试: '{item}'")
        
        # 方法2: Ray Actor 队列
        print("\n--- Ray Actor 队列示例 ---")
        actor_descriptor = QueueDescriptor.create_ray_actor_queue(
            actor_name="test_queue_actor",
            queue_id="test_actor_queue",
            maxsize=50
        )
        
        print(f"Ray Actor 描述符: {actor_descriptor}")
        
        actor_queue_stub = resolve_descriptor(actor_descriptor)
        print(f"Ray Actor 队列 Stub: {actor_queue_stub}")
        
        # 测试操作
        actor_queue_stub.put("Hello Ray Actor Queue!")
        actor_item = actor_queue_stub.get()
        print(f"Ray Actor 队列操作测试: '{actor_item}'")
        
        # 序列化测试
        json_str = actor_descriptor.to_json()
        restored = QueueDescriptor.from_json(json_str)
        print(f"序列化和恢复成功: {restored.queue_id}")
        
    except Exception as e:
        print(f"Ray Queue 示例失败: {e}")
        logger.exception("Ray Queue example failed")


def example_existing_queue_conversion():
    """
    演示从现有队列对象创建描述符
    """
    print("\n=== 现有队列转换示例 ===")
    
    try:
        # 1. 从现有 Python Queue 创建描述符
        from queue import Queue
        from sage.runtime.communication.queue_stubs import LocalQueueStub
        
        python_queue = Queue(maxsize=10)
        python_queue.put("test item")
        
        # 从现有队列创建 stub
        local_stub = LocalQueueStub.from_queue(
            python_queue, 
            queue_id="existing_python_queue"
        )
        
        print(f"从现有 Python Queue 创建的 Stub: {local_stub}")
        
        # 获取描述符
        descriptor = local_stub.to_descriptor()
        print(f"对应的描述符: {descriptor}")
        
        # 验证队列中的数据还在
        item = local_stub.get()
        print(f"从转换后的队列获取数据: '{item}'")
        
        # 2. 从现有 SAGE Queue 创建描述符 (如果 SAGE Queue 可用)
        try:
            from sage_ext.sage_queue.python.sage_queue import SageQueue
            from sage.runtime.communication.queue_stubs import SageQueueStub
            
            # 创建一个 SAGE Queue
            existing_sage_queue = SageQueue("existing_sage_test", maxsize=1024)
            existing_sage_queue.put("existing data")
            
            # 从现有 SAGE Queue 创建 stub
            sage_stub = SageQueueStub.from_sage_queue(
                existing_sage_queue,
                queue_id="existing_sage_queue",
                custom_metadata="additional info"
            )
            
            print(f"从现有 SAGE Queue 创建的 Stub: {sage_stub}")
            
            # 验证数据
            existing_data = sage_stub.get()
            print(f"从现有 SAGE Queue 获取数据: '{existing_data}'")
            
            sage_stub.close()
            
        except ImportError:
            print("SAGE Queue 不可用，跳过 SAGE Queue 转换示例")
        
    except Exception as e:
        print(f"现有队列转换示例失败: {e}")
        logger.exception("Existing queue conversion example failed")


def example_cross_process_usage():
    """
    演示跨进程队列传递的用法
    """
    print("\n=== 跨进程队列传递示例 ===")
    
    try:
        import multiprocessing
        from sage.runtime.communication.queue_descriptor import QueueDescriptor, resolve_descriptor
        
        def worker_process(descriptor_json: str):
            """工作进程函数"""
            try:
                # 从 JSON 恢复描述符
                descriptor = QueueDescriptor.from_json(descriptor_json)
                print(f"工作进程收到描述符: {descriptor.queue_id}")
                
                # 解析描述符得到队列
                queue = resolve_descriptor(descriptor)
                
                # 从队列获取任务
                while True:
                    try:
                        task = queue.get(timeout=1.0)
                        if task == "STOP":
                            break
                        print(f"工作进程处理任务: {task}")
                        
                        # 处理完成后放入结果
                        result = f"处理完成: {task}"
                        queue.put(result)
                        
                    except:
                        break
                
                print("工作进程结束")
                
            except Exception as e:
                print(f"工作进程错误: {e}")
        
        # 创建共享内存队列描述符
        descriptor = QueueDescriptor.create_shm_queue(
            shm_name="cross_process_test",
            queue_id="cross_process_queue",
            maxsize=100
        )
        
        # 创建队列
        main_queue = resolve_descriptor(descriptor)
        
        # 序列化描述符
        descriptor_json = descriptor.to_json()
        
        # 启动工作进程
        process = multiprocessing.Process(
            target=worker_process, 
            args=(descriptor_json,)
        )
        process.start()
        
        # 主进程发送任务
        tasks = ["任务1", "任务2", "任务3"]
        for task in tasks:
            main_queue.put(task)
            print(f"主进程发送任务: {task}")
        
        # 收集结果
        results = []
        for _ in tasks:
            try:
                result = main_queue.get(timeout=5.0)
                results.append(result)
                print(f"主进程收到结果: {result}")
            except:
                break
        
        # 发送停止信号
        main_queue.put("STOP")
        
        # 等待工作进程结束
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
        
        print(f"跨进程通信完成，收到 {len(results)} 个结果")
        
    except Exception as e:
        print(f"跨进程队列示例失败: {e}")
        logger.exception("Cross-process queue example failed")


def example_auto_queue_selection():
    """
    演示自动队列类型选择
    """
    print("\n=== 自动队列类型选择示例 ===")
    
    try:
        from sage.runtime.communication.queue_stubs import (
            auto_select_queue_type,
            create_auto_queue,
            list_supported_queue_types
        )
        
        # 列出支持的队列类型
        supported_types = list_supported_queue_types()
        print(f"支持的队列类型: {supported_types}")
        
        # 自动选择队列类型
        selected_type = auto_select_queue_type()
        print(f"自动选择的队列类型: {selected_type}")
        
        # 创建自动选择的队列
        auto_queue = create_auto_queue(
            queue_id="auto_selected_queue",
            maxsize=500
        )
        
        print(f"自动创建的队列: {auto_queue}")
        
        # 测试队列操作
        auto_queue.put("自动队列测试")
        item = auto_queue.get()
        print(f"自动队列操作测试: '{item}'")
        
        # 获取对应的描述符
        if hasattr(auto_queue, 'to_descriptor'):
            descriptor = auto_queue.to_descriptor()
            print(f"自动队列的描述符: {descriptor}")
        
    except Exception as e:
        print(f"自动队列选择示例失败: {e}")
        logger.exception("Auto queue selection example failed")


def main():
    """
    运行所有示例
    """
    print("开始运行队列转换示例...")
    
    # 运行各个示例
    example_sage_queue_conversion()
    example_ray_queue_conversion()
    example_existing_queue_conversion()
    example_auto_queue_selection()
    example_cross_process_usage()
    
    print("\n所有示例运行完成！")


if __name__ == "__main__":
    main()
