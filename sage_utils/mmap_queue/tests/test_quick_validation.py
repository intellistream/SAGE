#!/usr/bin/env python3
"""
快速验证SAGE Queue基本功能
Quick validation test for SAGE Queue basic functionality
"""

import sys
import os

# 添加上级目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def quick_test():
    print("SAGE Queue 快速验证测试")
    print("=" * 30)
    
    try:
        from sage_queue import SageQueue, destroy_queue
        print("✓ 导入成功")
        
        # 清理可能存在的旧队列
        queue_name = "quick_test"
        destroy_queue(queue_name)
        
        # 创建队列
        queue = SageQueue(queue_name, maxsize=4096)
        print("✓ 队列创建成功")
        
        # 基本操作
        queue.put("Hello")
        queue.put(42)
        queue.put([1, 2, 3])
        print("✓ 数据写入成功")
        
        item1 = queue.get()
        item2 = queue.get()
        item3 = queue.get()
        print(f"✓ 数据读取成功: {item1}, {item2}, {item3}")
        
        # 状态检查
        print(f"✓ 队列状态: empty={queue.empty()}, qsize={queue.qsize()}")
        
        # 统计信息
        stats = queue.get_stats()
        print(f"✓ 统计信息: 读={stats['total_bytes_read']}, 写={stats['total_bytes_written']}")
        
        # 队列引用
        ref = queue.get_reference()
        print(f"✓ 队列引用: {ref}")
        
        queue.close()
        print("✓ 队列关闭成功")
        
        print("\n🎉 所有测试通过!")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_test()
