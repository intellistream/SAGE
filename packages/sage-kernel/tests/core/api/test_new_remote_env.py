#!/usr/bin/env python3
"""
测试RemoteEnvironment序列化功能的简单脚本
"""

import sys
import os

def test_serialization():
    """测试序列化流程"""
    print("=== 测试 RemoteEnvironment 序列化流程 ===")
    
    try:
        from sage.api.remote_environment import RemoteEnvironment
        from sage.runtime.serialization.dill import trim_object_for_ray, serialize_object, deserialize_object
        
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
        trimmed_env = trim_object_for_ray(remote_env)
        print(f"   Trimmed successfully: {type(trimmed_env)}")
        if hasattr(trimmed_env, '__dict__'):
            print(f"   Trimmed attrs: {list(trimmed_env.__dict__.keys())}")
        
        # 3. 测试serialize_object
        print("\n3. Testing serialize_object...")
        serialized_data = serialize_object(trimmed_env)
        print(f"   Serialized successfully: {len(serialized_data)} bytes")
        
        # 4. 测试deserialize_object
        print("\n4. Testing deserialize_object...")
        deserialized_env = deserialize_object(serialized_data)
        print(f"   Deserialized successfully: {type(deserialized_env)}")
        print(f"   Name: {getattr(deserialized_env, 'name', 'N/A')}")
        print(f"   Config: {getattr(deserialized_env, 'config', 'N/A')}")
        
        print("\n✅ 序列化测试通过!")
        # Assert that the test succeeded
        assert deserialized_env is not None
        assert hasattr(deserialized_env, 'name')
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"测试失败: {e}"

def test_client():
    """测试JobManagerClient"""
    print("\n=== 测试 JobManagerClient ===")
    
    try:
        from sage.jobmanager.jobmanager_client import JobManagerClient
        
        client = JobManagerClient("127.0.0.1", 19001)
        print(f"Created client: {client.host}:{client.port}")
        
        # 列出可用方法
        methods = [method for method in dir(client) if not method.startswith('_')]
        print(f"Available methods: {methods}")
        
        print("\n✅ Client测试通过!")
        # Assert that the test succeeded
        assert client is not None
        assert hasattr(client, 'host')
        assert hasattr(client, 'port')
        
    except Exception as e:
        print(f"\n❌ Client测试失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Client测试失败: {e}"

def test_remote_env():
    """测试RemoteEnvironment方法"""
    print("\n=== 测试 RemoteEnvironment 方法 ===")
    
    try:
        from sage.api.remote_environment import RemoteEnvironment
        
        remote_env = RemoteEnvironment("test_env2")
        
        # 测试client属性
        client = remote_env.client
        print(f"Client created: {type(client)}")
        
        # 测试health_check（预期连接失败）
        result = remote_env.health_check()
        print(f"Health check result: {result}")
        
        # 测试get_job_status（没有作业）
        status = remote_env.get_job_status()
        print(f"Job status: {status}")
        
        print("\n✅ RemoteEnvironment方法测试通过!")
        # Assert that the test succeeded
        assert remote_env is not None
        assert client is not None
        
    except Exception as e:
        print(f"\n❌ RemoteEnvironment方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"RemoteEnvironment方法测试失败: {e}"

if __name__ == "__main__":
    print("开始测试 RemoteEnvironment 修改...")
    
    success1 = test_serialization()
    success2 = test_client()
    success3 = test_remote_env()
    
    if success1 and success2 and success3:
        print("\n🎉 所有测试都通过了!")
    else:
        print("\n❌ 有测试失败")
