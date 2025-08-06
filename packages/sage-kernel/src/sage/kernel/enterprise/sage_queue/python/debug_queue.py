#!/usr/bin/env python3
"""
调试脚本：分析队列读写问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sage.extensions.sage_queue.python.sage_queue import SageQueue
import pickle
import struct
import ctypes

def debug_queue_operations():
    print("=== SAGE Queue 调试 ===")

    # 创建队列
    queue = SageQueue("debug_queue", maxsize=1024)

    # 测试数据
    test_data = "Hello, World!"
    print(f"原始数据: {test_data}")

    # 1. 测试put操作
    print("\n1. 测试 PUT 操作...")
    queue.put(test_data)
    print(f"   ✓ PUT 成功")

    # 2. 检查队列状态
    print("\n2. 检查队列状态...")
    available_read = queue._lib.ring_buffer_available_read(queue._rb)
    available_write = queue._lib.ring_buffer_available_write(queue._rb)
    is_empty = queue._lib.ring_buffer_is_empty(queue._rb)
    size = queue._lib.ring_buffer_size(queue._rb)

    print(f"   可读字节数: {available_read}")
    print(f"   可写字节数: {available_write}")
    print(f"   队列是否为空: {is_empty}")
    print(f"   队列大小: {size}")

    # 3. 测试peek操作
    print("\n3. 测试 PEEK 操作...")
    if available_read >= 4:
        len_buffer = ctypes.create_string_buffer(4)
        result = queue._lib.ring_buffer_peek(queue._rb, len_buffer, 4)
        print(f"   PEEK 结果: {result}")
        if result == 4:
            data_len = struct.unpack('<I', len_buffer.raw)[0]
            print(f"   数据长度: {data_len}")
            total_len = 4 + data_len
            print(f"   总长度: {total_len}")

            # 检查是否有足够数据
            if available_read >= total_len:
                print(f"   ✓ 有足够数据可读")

                # 尝试读取完整数据
                full_buffer = ctypes.create_string_buffer(total_len)
                read_result = queue._lib.ring_buffer_read(queue._rb, full_buffer, total_len)
                print(f"   READ 结果: {read_result}")

                if read_result == total_len:
                    # 解析数据
                    raw_data = full_buffer.raw[4:4+data_len]
                    print(f"   原始数据长度: {len(raw_data)}")
                    try:
                        decoded_data = pickle.loads(raw_data)
                        print(f"   ✓ 解码成功: {decoded_data}")
                    except Exception as e:
                        print(f"   ❌ 解码失败: {e}")
                        print(f"   原始字节: {raw_data[:20]}...")
                else:
                    print(f"   ❌ READ 失败，期望 {total_len}，实际 {read_result}")
            else:
                print(f"   ❌ 数据不足，需要 {total_len}，可用 {available_read}")
        else:
            print(f"   ❌ PEEK 失败")
    else:
        print(f"   ❌ 可读数据不足4字节")

    # 4. 再次检查队列状态
    print("\n4. 操作后队列状态...")
    available_read_after = queue._lib.ring_buffer_available_read(queue._rb)
    size_after = queue._lib.ring_buffer_size(queue._rb)
    print(f"   可读字节数: {available_read_after}")
    print(f"   队列大小: {size_after}")

    queue.close()

if __name__ == "__main__":
    debug_queue_operations()
