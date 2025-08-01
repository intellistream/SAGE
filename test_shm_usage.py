#!/usr/bin/env python3
"""测试共享内存使用情况"""

import os
import time
from sage_ext.sage_queue.python.sage_queue import SageQueue

def test_shm_usage():
    print("测试共享内存使用情况...")
    
    # 检查初始状态
    print("初始共享内存状态:")
    os.system("df -h /dev/shm")
    os.system("ls -la /dev/shm/")
    
    queues = []
    try:
        # 创建多个队列
        for i in range(10):
            queue_name = f"test_shm_queue_{i}"
            print(f"创建队列 {queue_name}")
            queue = SageQueue(queue_name, maxsize=10000)
            queues.append(queue)
            
            # 检查共享内存状态
            print(f"创建第{i+1}个队列后:")
            os.system("ls -la /dev/shm/ | grep -v '^total'")
            
            # 添加一些数据
            for j in range(10):
                queue.put(f"test_message_{j}", timeout=1.0)
        
        print("所有队列创建完成，最终状态:")
        os.system("df -h /dev/shm")
        os.system("ls -la /dev/shm/")
        
    except Exception as e:
        print(f"出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        print("清理队列...")
        for queue in queues:
            try:
                queue.close()
            except:
                pass
        
        print("清理后状态:")
        os.system("ls -la /dev/shm/")

if __name__ == "__main__":
    test_shm_usage()
