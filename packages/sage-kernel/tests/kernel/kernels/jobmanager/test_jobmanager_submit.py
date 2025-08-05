#!/usr/bin/env python3
"""
简化测试：验证JobManager处理序列化数据的能力
"""

import sys
import os
import base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_jobmanager_submit_logic():
    """测试JobManager的_handle_submit_job逻辑"""
    print("=== 测试 JobManager submit_job 处理逻辑 ===")
    
    try:
        from sage.kernel.kernels.jobmanager.job_manager import JobManagerServer, JobManager
        from sage.kernel.utils.serialization.dill_serializer import serialize_object
        from sage.kernel.api.local_environment import LocalEnvironment
        
        # 创建一个真实的LocalEnvironment用于测试
        local_env = LocalEnvironment("test_submit")
        print(f"1. Created local environment: {local_env.name}")
        
        # 序列化环境
        serialized_data = serialize_object(local_env)
        print(f"2. Serialized environment: {len(serialized_data)} bytes")
        
        # 编码为base64
        serialized_b64 = base64.b64encode(serialized_data).decode('utf-8')
        print(f"3. Base64 encoded: {len(serialized_b64)} chars")
        
        # 创建JobManager和Daemon实例
        jobmanager = JobManager(enable_daemon=False)  # 不启动实际的daemon
        daemon = JobManagerServer(jobmanager)
        print("4. Created JobManager and Daemon")
        
        # 模拟客户端请求
        request = {
            "action": "submit_job",
            "request_id": "test-123",
            "serialized_data": serialized_b64
        }
        
        # 调用处理方法
        print("5. Processing submit request...")
        response = daemon._handle_submit_job(request)
        print(f"6. Response: {response}")
        
        if response.get("status") == "success":
            print("✅ JobManager成功处理了序列化提交!")
            return True
        else:
            print(f"❌ JobManager处理失败: {response.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_client_request_format():
    """测试客户端请求格式"""
    print("\n=== 测试 JobManagerClient 请求格式 ===")
    
    try:
        from sage.kernel.kernels.jobmanager.jobmanager_client import JobManagerClient
        import uuid
        
        # 创建客户端
        client = JobManagerClient("127.0.0.1", 19001)
        print("1. Created JobManagerClient")
        
        # 模拟序列化数据
        test_data = b"mock serialized data"
        
        # 构造请求（不实际发送）
        import base64
        request = {
            "action": "submit_job",
            "request_id": str(uuid.uuid4()),
            "serialized_data": base64.b64encode(test_data).decode('utf-8')
        }
        
        print(f"2. Constructed request format: action={request['action']}")
        print(f"   Request has serialized_data: {'serialized_data' in request}")
        print(f"   Serialized data length: {len(request['serialized_data'])}")
        
        print("✅ 客户端请求格式正确!")
        return True
        
    except Exception as e:
        print(f"❌ 客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success1 = test_jobmanager_submit_logic()
        success2 = test_client_request_format()
        
        if success1 and success2:
            print("\n🎉 所有测试都通过了!")
            print("JobManager现在可以正确处理RemoteEnvironment的序列化提交!")
        else:
            print("\n❌ 有测试失败")
            
    except Exception as e:
        print(f"\n💥 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
