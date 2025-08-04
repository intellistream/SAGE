#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 清理工具
Cleanup tool for SAGE high-performance memory-mapped queue
"""

import os
import sys
import glob
import time

def cleanup_shared_memory():
    """清理共享内存中的SAGE队列文件"""
    print("SAGE Memory-Mapped Queue 清理工具")
    print("=" * 40)
    
    shm_pattern = "/dev/shm/sage_ringbuf_*"
    sage_files = glob.glob(shm_pattern)
    
    if not sage_files:
        print("✓ 没有发现SAGE共享内存文件")
        return
    
    print(f"发现 {len(sage_files)} 个SAGE共享内存文件:")
    
    removed = 0
    failed = 0
    
    for file_path in sage_files:
        filename = os.path.basename(file_path)
        try:
            file_size = os.path.getsize(file_path)
            os.unlink(file_path)
            print(f"  ✓ 删除: {filename} ({file_size} 字节)")
            removed += 1
        except Exception as e:
            print(f"  ✗ 删除失败: {filename} - {e}")
            failed += 1
    
    print("-" * 40)
    print(f"清理完成: {removed} 个文件删除, {failed} 个失败")
    
    if removed > 0:
        print("\n✓ 共享内存清理成功")
    elif failed > 0:
        print("\n⚠️  部分文件清理失败")
    else:
        print("\n✓ 无需清理")


if __name__ == "__main__":
    cleanup_shared_memory()
