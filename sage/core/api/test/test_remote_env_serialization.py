#!/usr/bin/env python3
"""
测试RemoteEnvironment的序列化提交流程
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 添加项目路径
from sage.core.api.remote_environment import RemoteEnvironment
from sage.utils.serialization.dill_serializer import trim_object_for_ray, serialize_object, deserialize_object

def test_remote_environment_serialization():
    """测试RemoteEnvironment的序列化过程"""
    print("=== 测试 RemoteEnvironment 序列化流程 ===")
    
    # 1. 创建RemoteEnvironment实例
    print("1. Creating RemoteEnvironment...")
    remote_env = RemoteEnvironment(
        name="test_env",
        config={"test_key": "test_value"},
        host="127.0.0.1",
        port=19001
    )
    
    print(f"   Created: {remote_env}")
    print(f"   Config: {remote_env.config}")
    print(f"   Excluded attrs: {remote_env.__state_exclude__}")
    
    # 2. 测试trim_object_for_ray
    print("\n2. Testing trim_object_for_ray...")
    try:
        trimmed_env = trim_object_for_ray(remote_env)
        print(f"   Trimmed successfully: {type(trimmed_env)}")
        print(f"   Trimmed object has __dict__: {hasattr(trimmed_env, '__dict__')}")
        if hasattr(trimmed_env, '__dict__'):
            print(f"   Trimmed attrs: {list(trimmed_env.__dict__.keys())}")
    except Exception as e:
        print(f"   Error during trimming: {e}")
        return False
    
    # 3. 测试serialize_object
    print("\n3. Testing serialize_object...")
    try:
        serialized_data = serialize_object(trimmed_env)
        print(f"   Serialized successfully: {len(serialized_data)} bytes")
    except Exception as e:
        print(f"   Error during serialization: {e}")
        return False
    
    # 4. 测试deserialize_object
    print("\n4. Testing deserialize_object...")
    try:
        deserialized_env = deserialize_object(serialized_data)
        print(f"   Deserialized successfully: {type(deserialized_env)}")
        print(f"   Name: {getattr(deserialized_env, 'name', 'N/A')}")
        print(f"   Config: {getattr(deserialized_env, 'config', 'N/A')}")
    except Exception as e:
        print(f"   Error during deserialization: {e}")
        return False
    
    print("\n✅ 所有序列化测试通过!")
    return True

def test_client_methods():
    """测试JobManagerClient的方法（不实际连接）"""
    print("\n=== 测试 JobManagerClient 方法 ===")
    
    from sage.jobmanager.jobmanager_client import JobManagerClient
    
    client = JobManagerClient("127.0.0.1", 19001)
    print(f"Created client: {client.host}:{client.port}")
    
    # 测试请求构造（不实际发送）
    print("Client methods available:")
    methods = [method for method in dir(client) if not method.startswith('_')]
    for method in methods:
        print(f"  - {method}")
    
    print("\n✅ Client测试通过!")
    return True

def test_remote_environment_methods():
    """测试RemoteEnvironment的新方法（不实际连接）"""
    print("\n=== 测试 RemoteEnvironment 方法 ===")
    
    remote_env = RemoteEnvironment("test_env2")
    
    # 测试client属性的延迟创建
    print("Testing client property...")
    client = remote_env.client
    print(f"Client created: {type(client)}")
    
    # 测试health_check（会因为连接失败而返回错误，但这是预期的）
    print("\nTesting health_check (expected to fail with connection error)...")
    result = remote_env.health_check()
    print(f"Health check result: {result}")
    
    # 测试get_job_status（没有提交的作业）
    print("\nTesting get_job_status (no job submitted)...")
    status = remote_env.get_job_status()
    print(f"Job status: {status}")
    
    print("\n✅ RemoteEnvironment方法测试通过!")
    return True

if __name__ == "__main__":
    try:
        success1 = test_remote_environment_serialization()
        success2 = test_client_methods()
        success3 = test_remote_environment_methods()
        
        if success1 and success2 and success3:
            print("\n🎉 所有测试都通过了!")
            sys.exit(0)
        else:
            print("\n❌ 有测试失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

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
