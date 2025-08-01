#!/usr/bin/env python3
"""调试队列导入问题"""

import os
import sys
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

def test_import_in_subprocess():
    """在子进程中测试导入"""
    try:
        print(f"Process {os.getpid()}: Working directory: {os.getcwd()}")
        print(f"Process {os.getpid()}: Python path: {sys.path[:3]}")
        
        from sage_ext.sage_queue.python.sage_queue import SageQueue
        print(f"Process {os.getpid()}: SageQueue import successful")
        
        # 尝试创建队列
        queue = SageQueue("test_queue", maxsize=100)
        print(f"Process {os.getpid()}: Queue creation successful")
        
        # 测试基本操作
        queue.put("test_message")
        msg = queue.get(timeout=1)
        print(f"Process {os.getpid()}: Basic operations successful: {msg}")
        
        queue.close()
        return True
        
    except Exception as e:
        print(f"Process {os.getpid()}: Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Testing queue import in main process...")
    result = test_import_in_subprocess()
    print(f"Main process result: {result}")
    
    print("\nTesting queue import in subprocess...")
    with ProcessPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(test_import_in_subprocess) for _ in range(2)]
        for i, future in enumerate(futures):
            try:
                result = future.result(timeout=10)
                print(f"Subprocess {i} result: {result}")
            except Exception as e:
                print(f"Subprocess {i} failed: {e}")

if __name__ == "__main__":
    main()
