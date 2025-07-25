#!/usr/bin/env python3
"""
专门用于测试 RemoteEnvironment 序列化的简化脚本
"""

import sys
import os
import threading
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入测试服务器
from sage.core.api.test.test_remote_environment_server import (
    EnvironmentTestServer,
    send_test_environment,
    send_remote_environment_test,
    run_remote_environment_test
)

def main():
    """
    运行RemoteEnvironment序列化的完整测试
    """
    print("🧪 SAGE RemoteEnvironment 序列化测试")
    print("="*50)
    
    # 测试基本序列化
    print("\n1. 基础序列化测试...")
    basic_success = run_remote_environment_test(port=19003)
    
    # 尝试使用不同的序列化方法
    print("\n2. 测试不同的序列化方法...")
    
    # 启动测试服务器
    server = EnvironmentTestServer("127.0.0.1", 19004)
    
    def run_server():
        try:
            server.start()
        except:
            pass
    
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(1)  # 等待服务器启动
    
    try:
        # 测试基础数据
        print("   📋 测试字典序列化...")
        send_test_environment("127.0.0.1", 19004)
        
        # 测试RemoteEnvironment
        print("   🎯 测试RemoteEnvironment序列化...")
        remote_success = send_remote_environment_test("127.0.0.1", 19004)
        
        time.sleep(1)
        
        # 显示结果
        stats = server.get_stats()
        summary = server.get_environment_summary()
        
        print(f"\n📊 测试结果:")
        print(f"   - 处理的环境数量: {stats['received_count']}")
        print(f"   - 基础测试: {'✅ 通过' if basic_success else '❌ 失败'}")
        print(f"   - RemoteEnvironment测试: {'✅ 通过' if remote_success else '❌ 失败'}")
        
        # 显示详细信息
        for env in summary.get("environments", []):
            print(f"   - 环境 {env['id']}: {env['type']} ({env['name']}) - {'✅' if env['valid'] else '❌'}")
        
        overall_success = basic_success and remote_success
        
        print(f"\n🎉 总体结果: {'✅ 所有测试通过' if overall_success else '❌ 部分测试失败'}")
        print("="*50)
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        return False
    finally:
        server.stop()

if __name__ == "__main__":
    success = main()
    print(f"\n退出代码: {0 if success else 1}")
    sys.exit(0 if success else 1)
