#!/usr/bin/env python3
"""
重现 SAGE Queue bad_alloc 问题的测试
"""

import time
import gc
from sage_ext.sage_queue.python.sage_queue import SageQueue

def test_rapid_put_operations():
    """测试快速连续的 put 操作"""
    print("测试快速连续的 put 操作...")
    
    try:
        # 使用与性能测试相同的配置
        queue = SageQueue(
            name="perf_test_reproduce",
            maxsize=10*1024*1024,  # 10MB
            auto_cleanup=True
        )
        
        print("队列创建成功，开始快速 put 操作...")
        
        # 快速连续的 put 操作，就像性能测试一样
        start_time = time.time()
        for i in range(1000):  # 先尝试1000个
            try:
                queue.put(f"item_{i}")
                if i % 100 == 0:
                    print(f"已添加 {i} 个项目")
            except Exception as e:
                print(f"在第 {i} 个项目时失败: {e}")
                break
        
        end_time = time.time()
        print(f"put 操作完成，耗时: {end_time - start_time:.3f} 秒")
        
        # 清空队列
        print("开始清空队列...")
        count = 0
        while not queue.empty():
            try:
                item = queue.get()
                count += 1
                if count % 100 == 0:
                    print(f"已获取 {count} 个项目")
            except Exception as e:
                print(f"获取第 {count} 个项目时失败: {e}")
                break
        
        print(f"总共获取了 {count} 个项目")
        queue.close()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_memory_pressure():
    """测试内存压力情况"""
    print("\n测试内存压力情况...")
    
    try:
        # 创建多个队列，模拟测试环境
        queues = []
        
        for i in range(3):  # 创建3个队列
            queue_name = f"pressure_test_{i}"
            queue = SageQueue(
                name=queue_name,
                maxsize=10*1024*1024,
                auto_cleanup=True
            )
            queues.append(queue)
            print(f"创建队列 {i+1}/3")
        
        # 在每个队列中添加数据
        for i, queue in enumerate(queues):
            print(f"在队列 {i+1} 中添加数据...")
            for j in range(500):
                try:
                    queue.put(f"queue_{i}_item_{j}")
                except Exception as e:
                    print(f"队列 {i+1} 在第 {j} 个项目时失败: {e}")
                    break
        
        # 清理
        for i, queue in enumerate(queues):
            try:
                queue.close()
                print(f"队列 {i+1} 关闭成功")
            except Exception as e:
                print(f"队列 {i+1} 关闭失败: {e}")
                
    except Exception as e:
        print(f"内存压力测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_large_items():
    """测试大型项目"""
    print("\n测试大型项目...")
    
    try:
        queue = SageQueue(
            name="large_items_test",
            maxsize=50*1024*1024,  # 50MB
            auto_cleanup=True
        )
        
        # 创建较大的项目
        large_item = "x" * (1024 * 100)  # 100KB
        print(f"尝试添加 100KB 的项目...")
        
        for i in range(100):  # 添加100个100KB的项目
            try:
                queue.put(f"large_item_{i}_{large_item}")
                if i % 10 == 0:
                    print(f"已添加 {i+1} 个大项目")
            except Exception as e:
                print(f"在第 {i} 个大项目时失败: {e}")
                break
        
        print("大项目测试完成")
        queue.close()
        
    except Exception as e:
        print(f"大项目测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("SAGE Queue bad_alloc 问题重现测试")
    print("=" * 50)
    
    # 清理旧的共享内存
    import subprocess
    import os
    try:
        result = subprocess.run(['ls', '/dev/shm/'], capture_output=True, text=True)
        if result.returncode == 0:
            files = result.stdout.split()
            test_files = [f for f in files if 'test' in f.lower() or 'perf' in f.lower()]
            for file in test_files:
                try:
                    os.unlink(f'/dev/shm/{file}')
                    print(f"清理共享内存文件: {file}")
                except:
                    pass
    except:
        pass
    
    # 运行测试
    test_rapid_put_operations()
    test_memory_pressure()
    test_large_items()
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()
