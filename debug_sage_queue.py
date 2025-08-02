#!/usr/bin/env python3
"""
SAGE Queue 调试脚本
"""

import os
import sys
import ctypes

def check_shared_memory():
    """检查共享内存状况"""
    print("\n=== 共享内存检查 ===")
    
    # 检查 /dev/shm 可用空间
    try:
        stat = os.statvfs('/dev/shm')
        available_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        print(f"可用共享内存: {available_mb:.1f} MB")
        
        # 列出现有的共享内存文件
        shm_files = []
        if os.path.exists('/dev/shm'):
            for f in os.listdir('/dev/shm'):
                if 'sage' in f.lower() or 'ring' in f.lower():
                    shm_files.append(f)
        
        if shm_files:
            print(f"现有 SAGE 相关共享内存文件: {shm_files}")
        else:
            print("没有找到现有的 SAGE 相关共享内存文件")
            
    except Exception as e:
        print(f"检查共享内存时出错: {e}")

def check_library():
    """检查库文件"""
    print("\n=== 库文件检查 ===")
    
    # 查找库文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sage_queue_dir = os.path.join(current_dir, 'sage_ext', 'sage_queue', 'python')
    
    lib_paths = [
        os.path.join(sage_queue_dir, "libring_buffer.so"),
        os.path.join(sage_queue_dir, "ring_buffer.so"),
    ]
    
    for lib_path in lib_paths:
        if os.path.exists(lib_path):
            print(f"找到库文件: {lib_path}")
            # 尝试加载
            try:
                lib = ctypes.CDLL(lib_path)
                print(f"成功加载库: {lib_path}")
                
                # 检查函数是否存在
                if hasattr(lib, 'ring_buffer_create_named'):
                    print("✓ ring_buffer_create_named 函数存在")
                else:
                    print("✗ ring_buffer_create_named 函数不存在")
                    
                break
            except Exception as e:
                print(f"加载库失败: {lib_path} - {e}")
        else:
            print(f"库文件不存在: {lib_path}")

def test_small_queue():
    """测试小型队列"""
    print("\n=== 小型队列测试 ===")
    
    try:
        from sage_ext.sage_queue.python.sage_queue import SageQueue
        
        # 创建一个很小的队列来测试
        print("尝试创建小型队列 (1KB)...")
        queue = SageQueue(
            name="debug_small_test",
            maxsize=1024,  # 1KB
            auto_cleanup=True
        )
        
        print("✓ 小型队列创建成功")
        
        # 尝试 put 一个小项目
        print("尝试添加小项目...")
        queue.put("test_message")
        print("✓ 添加成功")
        
        # 尝试 get
        print("尝试获取项目...")
        result = queue.get()
        print(f"✓ 获取成功: {result}")
        
        queue.close()
        print("✓ 队列关闭成功")
        
    except Exception as e:
        print(f"✗ 小型队列测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_large_queue():
    """测试大型队列"""
    print("\n=== 大型队列测试 ===")
    
    try:
        from sage_ext.sage_queue.python.sage_queue import SageQueue
        
        # 创建一个大队列 (10MB)
        print("尝试创建大型队列 (10MB)...")
        queue = SageQueue(
            name="debug_large_test",
            maxsize=10*1024*1024,  # 10MB
            auto_cleanup=True
        )
        
        print("✓ 大型队列创建成功")
        
        # 尝试添加一些项目
        print("尝试添加多个项目...")
        for i in range(100):
            queue.put(f"test_message_{i}")
            if i % 10 == 0:
                print(f"  已添加 {i+1} 个项目")
        
        print("✓ 添加100个项目成功")
        
        # 尝试获取项目
        print("尝试获取项目...")
        for i in range(100):
            result = queue.get()
            if i % 10 == 0:
                print(f"  已获取 {i+1} 个项目: {result}")
        
        print("✓ 获取所有项目成功")
        
        queue.close()
        print("✓ 大型队列关闭成功")
        
    except Exception as e:
        print(f"✗ 大型队列测试失败: {e}")
        import traceback
        traceback.print_exc()

def cleanup_shared_memory():
    """清理共享内存"""
    print("\n=== 清理共享内存 ===")
    
    try:
        import subprocess
        
        # 查找并删除相关的共享内存文件
        result = subprocess.run(['ls', '/dev/shm/'], capture_output=True, text=True)
        if result.returncode == 0:
            files = result.stdout.split()
            sage_files = [f for f in files if 'sage' in f.lower() or 'ring' in f.lower() or 'debug' in f.lower()]
            
            for file in sage_files:
                file_path = f'/dev/shm/{file}'
                try:
                    os.unlink(file_path)
                    print(f"删除共享内存文件: {file_path}")
                except Exception as e:
                    print(f"删除失败 {file_path}: {e}")
        
    except Exception as e:
        print(f"清理共享内存时出错: {e}")

def main():
    print("SAGE Queue 调试工具")
    print("=" * 50)
    
    check_shared_memory()
    check_library()
    
    # 先清理旧的共享内存
    cleanup_shared_memory()
    
    # 测试小队列
    test_small_queue()
    
    # 测试大队列
    test_large_queue()
    
    print("\n调试完成!")

if __name__ == "__main__":
    main()
