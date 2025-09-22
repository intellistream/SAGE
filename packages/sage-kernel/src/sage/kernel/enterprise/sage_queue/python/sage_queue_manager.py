#!/usr/bin/env python3
"""
SAGE队列管理工具

这个工具提供了管理SAGE共享内存队列的命令行接口，包括：
- 列出所有队列
- 清理死进程的队列
- 清理指定用户的所有队列
- 显示队列统计信息
"""

import sys
import os
import argparse
sys.path.insert(0, '/home/tjy/SAGE')

from sage.extensions.sage_queue.python.sage_queue import (
    SageQueue, 
    cleanup_invalid_queues, 
    cleanup_user_queues,
    list_all_sage_queues
)

def main():
    parser = argparse.ArgumentParser(
        description="SAGE队列管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s list                    # 列出所有队列
  %(prog)s cleanup                 # 清理死进程的队列
  %(prog)s cleanup-user            # 清理当前用户的所有队列
  %(prog)s cleanup-user cyb        # 清理用户cyb的所有队列
  %(prog)s cleanup-user tjy --force # 强制清理用户tjy的所有队列（包括活跃进程）
  %(prog)s test TestQueue          # 创建并测试队列
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # list命令
    list_parser = subparsers.add_parser('list', help='列出所有SAGE队列')
    
    # cleanup命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理队列')
    cleanup_parser.add_argument('--invalid', action='store_true', help='只清理无效队列（进程已死）')
    cleanup_parser.add_argument('--all', action='store_true', help='清理所有当前用户的队列')
    cleanup_parser.add_argument('--quiet', action='store_true', help='静默模式，不显示详细信息')
    
    # cleanup-user命令
    cleanup_user_parser = subparsers.add_parser('cleanup-user', help='清理指定用户的队列')
    cleanup_user_parser.add_argument('user', nargs='?', help='用户名（默认为当前用户）')
    cleanup_user_parser.add_argument('--force', action='store_true', 
                                    help='强制清理（包括活跃进程的队列）')
    cleanup_user_parser.add_argument('--quiet', action='store_true', help='静默模式，不显示详细信息')
    
    # test命令
    test_parser = subparsers.add_parser('test', help='创建并测试队列')
    test_parser.add_argument('queue_name', help='队列名称')
    test_parser.add_argument('--no-multi-tenant', action='store_true', 
                           help='禁用多租户模式')
    test_parser.add_argument('--auto-cleanup', action='store_true', 
                           help='启用自动清理')
    test_parser.add_argument('--namespace', help='自定义命名空间')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'list':
            print("=== SAGE队列列表 ===")
            list_all_sage_queues()
            
        elif args.command == 'cleanup':
            if args.all and args.invalid:
                print("错误：--all 和 --invalid 不能同时使用")
                return
            
            if not args.quiet:
                if args.all:
                    print("=== 清理当前用户的所有队列 ===")
                else:
                    print("=== 清理死进程的队列 ===")
            
            if args.all:
                # 清理当前用户的所有队列
                import getpass
                current_user = getpass.getuser()
                cleanup_user_queues(current_user, force=True)
            else:
                # 默认清理死进程队列
                cleanup_invalid_queues()
            print("清理完成")
            
        elif args.command == 'cleanup-user':
            if not args.user:
                import getpass
                user = getpass.getuser()
            else:
                user = args.user
            
            if not args.quiet:
                print(f"=== 清理用户 {user} 的队列 ===")
            cleanup_user_queues(user, force=args.force)
            
        elif args.command == 'test':
            queue_name = args.queue_name
            enable_multi_tenant = not args.no_multi_tenant
            auto_cleanup = args.auto_cleanup
            namespace = args.namespace
            
            print(f"=== 测试队列: {queue_name} ===")
            print(f"多租户模式: {enable_multi_tenant}")
            print(f"自动清理: {auto_cleanup}")
            print(f"命名空间: {namespace or '默认'}")
            
            # 创建队列
            queue = SageQueue(
                queue_name, 
                auto_cleanup=auto_cleanup,
                namespace=namespace,
                enable_multi_tenant=enable_multi_tenant
            )
            
            # 显示信息
            info = queue.get_shared_memory_info()
            stats = queue.get_stats()
            
            print(f"\n队列信息:")
            print(f"  原始名称: {info['original_name']}")
            print(f"  命名空间名称: {info['namespaced_name']}")
            print(f"  共享内存路径: {info['shm_path']}")
            print(f"  缓冲区大小: {stats['buffer_size']} 字节")
            print(f"  可用写入: {stats['available_write']} 字节")
            print(f"  引用计数: {stats['ref_count']}")
            
            # 测试读写
            print(f"\n测试读写:")
            test_message = f"测试消息 - {queue_name}"
            queue.put(test_message)
            print(f"  发送: {test_message}")
            
            received = queue.get()
            print(f"  接收: {received}")
            
            if test_message == received:
                print("  ✅ 读写测试成功")
            else:
                print("  ❌ 读写测试失败")
            
            # 关闭队列
            queue.close()
            print(f"\n队列已关闭")
            
            if auto_cleanup:
                print("共享内存应该已被自动清理")
            else:
                print("共享内存仍然存在，可以在其他进程中使用")
                
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
