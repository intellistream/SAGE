#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 诊断工具
Diagnostic tool for SAGE high-performance memory-mapped queue
"""

import os
import sys
import time
import threading
from typing import Dict, Any

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sage_queue import SageQueue, SageQueueRef, destroy_queue
    print("✓ 成功导入 SageQueue")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)


def diagnose_queue_behavior():
    """诊断队列行为"""
    print("\n=== 队列行为诊断 ===")
    
    queue_name = f"diagnose_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=1024)
        
        print("1. 测试基本put/get行为...")
        
        # 写入几条消息
        messages = ["msg1", "msg2", "msg3"]
        for i, msg in enumerate(messages):
            queue.put(msg)
            stats = queue.get_stats()
            print(f"   写入 '{msg}': qsize={queue.qsize()}, stats_msg_count={stats['message_count']}, available_read={stats['available_read']}")
        
        print("\n2. 测试读取行为...")
        read_messages = []
        while not queue.empty():
            msg = queue.get()
            read_messages.append(msg)
            stats = queue.get_stats()
            print(f"   读取 '{msg}': qsize={queue.qsize()}, stats_msg_count={stats['message_count']}, available_read={stats['available_read']}")
        
        print(f"\n   原始消息: {messages}")
        print(f"   读取消息: {read_messages}")
        print(f"   消息匹配: {messages == read_messages}")
        
        print("\n3. 测试队列填满行为...")
        
        test_msg = {"data": "x" * 50}  # 约50字节
        put_count = 0
        
        while True:
            try:
                queue.put_nowait(test_msg)
                put_count += 1
                if put_count % 5 == 0:
                    stats = queue.get_stats()
                    print(f"   已写入 {put_count}: available_write={stats['available_write']}, qsize={queue.qsize()}")
                
                if put_count > 50:  # 安全限制
                    break
                    
            except Exception as e:
                print(f"   写入失败 (第{put_count+1}次): {e}")
                break
        
        final_stats = queue.get_stats()
        print(f"\n   最终写入统计: {final_stats}")
        
        print("\n4. 测试队列读空行为...")
        
        get_count = 0
        while True:
            try:
                msg = queue.get_nowait()
                get_count += 1
                if get_count % 5 == 0:
                    stats = queue.get_stats()
                    print(f"   已读取 {get_count}: available_read={stats['available_read']}, qsize={queue.qsize()}")
                
                if get_count > put_count + 10:  # 安全限制
                    break
                    
            except Exception as e:
                print(f"   读取失败 (第{get_count+1}次): {e}")
                break
        
        final_empty_stats = queue.get_stats()
        print(f"\n   最终读取统计: {final_empty_stats}")
        print(f"   写入计数: {put_count}, 读取计数: {get_count}")
        
        queue.close()
        destroy_queue(queue_name)
        
    except Exception as e:
        print(f"诊断失败: {e}")
        import traceback
        traceback.print_exc()


def diagnose_threading_safety():
    """诊断线程安全性"""
    print("\n=== 线程安全性诊断 ===")
    
    queue_name = f"thread_diagnose_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=5000)
        
        results = {'put_count': 0, 'get_count': 0, 'errors': []}
        lock = threading.Lock()
        
        def producer():
            try:
                for i in range(20):
                    msg = {"producer_msg": i, "data": f"data_{i}"}
                    queue.put(msg, timeout=5.0)
                    
                    with lock:
                        results['put_count'] += 1
                    
                    if i % 5 == 0:
                        stats = queue.get_stats()
                        print(f"   Producer: 写入第{i}条, qsize={queue.qsize()}, available_read={stats['available_read']}")
                    
                    time.sleep(0.01)
                    
            except Exception as e:
                with lock:
                    results['errors'].append(f"Producer error: {e}")
        
        def consumer():
            try:
                for i in range(20):
                    msg = queue.get(timeout=10.0)
                    
                    with lock:
                        results['get_count'] += 1
                    
                    if i % 5 == 0:
                        stats = queue.get_stats()
                        print(f"   Consumer: 读取第{i}条, qsize={queue.qsize()}, available_read={stats['available_read']}")
                    
                    time.sleep(0.01)
                    
            except Exception as e:
                with lock:
                    results['errors'].append(f"Consumer error: {e}")
        
        # 启动线程
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        producer_thread.start()
        time.sleep(0.1)  # 稍微延迟启动消费者
        consumer_thread.start()
        
        producer_thread.join(timeout=15.0)
        consumer_thread.join(timeout=15.0)
        
        print(f"\n   最终结果: put={results['put_count']}, get={results['get_count']}")
        
        if results['errors']:
            print("   错误列表:")
            for error in results['errors']:
                print(f"     - {error}")
        else:
            print("   无错误发生")
        
        final_stats = queue.get_stats()
        print(f"   最终队列状态: {final_stats}")
        
        queue.close()
        destroy_queue(queue_name)
        
    except Exception as e:
        print(f"线程安全性诊断失败: {e}")
        import traceback
        traceback.print_exc()


def diagnose_memory_usage():
    """诊断内存使用"""
    print("\n=== 内存使用诊断 ===")
    
    queue_name = f"memory_diagnose_{int(time.time())}"
    
    try:
        destroy_queue(queue_name)
        
        # 测试不同缓冲区大小
        buffer_sizes = [1024, 4096, 16384, 65536]  # 1KB, 4KB, 16KB, 64KB
        
        for buffer_size in buffer_sizes:
            print(f"\n  测试缓冲区大小: {buffer_size} 字节")
            
            test_queue_name = f"{queue_name}_{buffer_size}"
            queue = SageQueue(test_queue_name, maxsize=buffer_size)
            
            # 测试能写入多少消息
            test_message = {"id": 0, "data": "x" * 100}  # 约100字节
            
            write_count = 0
            start_time = time.time()
            
            while True:
                try:
                    test_message['id'] = write_count
                    queue.put_nowait(test_message)
                    write_count += 1
                    
                    if write_count > buffer_size // 50:  # 防止无限循环
                        break
                        
                except:
                    break
            
            write_time = time.time() - start_time
            stats = queue.get_stats()
            
            print(f"    最大写入消息数: {write_count}")
            print(f"    缓冲区利用率: {stats['utilization']:.1%}")
            print(f"    写入速度: {write_count/write_time:.0f} msg/s" if write_time > 0 else "写入速度: N/A")
            
            # 读取验证
            read_count = 0
            while not queue.empty():
                try:
                    queue.get_nowait()
                    read_count += 1
                except:
                    break
            
            print(f"    成功读取: {read_count}/{write_count}")
            
            queue.close()
            destroy_queue(test_queue_name)
        
    except Exception as e:
        print(f"内存使用诊断失败: {e}")
        import traceback
        traceback.print_exc()


def diagnose_c_library():
    """诊断C库状态"""
    print("\n=== C库状态诊断 ===")
    
    try:
        # 检查库文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        lib_files = ["ring_buffer.so", "libring_buffer.so"]
        
        print("1. 检查库文件:")
        for lib_file in lib_files:
            lib_path = os.path.join(current_dir, lib_file)
            if os.path.exists(lib_path):
                stat = os.stat(lib_path)
                print(f"   ✓ {lib_file}: 大小={stat.st_size} 字节, 修改时间={time.ctime(stat.st_mtime)}")
            else:
                print(f"   ✗ {lib_file}: 不存在")
        
        # 测试库加载
        print("\n2. 测试库加载:")
        queue_name = f"lib_test_{int(time.time())}"
        destroy_queue(queue_name)
        
        try:
            queue = SageQueue(queue_name, maxsize=1024)
            print("   ✓ C库加载成功")
            
            # 测试基本函数
            queue.put("test")
            msg = queue.get()
            print("   ✓ 基本读写功能正常")
            
            stats = queue.get_stats()
            print(f"   ✓ 统计功能正常: {stats}")
            
            ref = queue.get_reference()
            print(f"   ✓ 引用功能正常: {ref}")
            
            queue.close()
            destroy_queue(queue_name)
            
        except Exception as e:
            print(f"   ✗ C库功能异常: {e}")
        
        print("\n3. 检查共享内存:")
        # 在Linux上检查/dev/shm/
        shm_dir = "/dev/shm"
        if os.path.exists(shm_dir):
            sage_files = [f for f in os.listdir(shm_dir) if f.startswith("sage_ringbuf_")]
            if sage_files:
                print(f"   发现 {len(sage_files)} 个SAGE共享内存文件:")
                for f in sage_files[:5]:  # 只显示前5个
                    file_path = os.path.join(shm_dir, f)
                    size = os.path.getsize(file_path)
                    print(f"     - {f}: {size} 字节")
                if len(sage_files) > 5:
                    print(f"     ... 还有 {len(sage_files) - 5} 个文件")
            else:
                print("   ✓ 无遗留共享内存文件")
        else:
            print("   ? 无法访问共享内存目录")
        
    except Exception as e:
        print(f"C库诊断失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主诊断函数"""
    print("SAGE Memory-Mapped Queue 诊断工具")
    print("=" * 50)
    
    diagnose_c_library()
    diagnose_queue_behavior()
    diagnose_threading_safety()
    diagnose_memory_usage()
    
    print("\n" + "=" * 50)
    print("诊断完成!")


if __name__ == "__main__":
    main()
