#!/usr/bin/env python3
"""
测试RemoteEnvironment与JobManager的端到端提交流程
"""

import sys
import os
import time
import threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_remote_submission_flow():
    """测试完整的远程提交流程"""
    print("=== 测试 RemoteEnvironment 与 JobManager 端到端流程 ===")
    
    # 1. 启动JobManager（在后台线程中）
    print("1. Starting JobManager...")
    
    def start_jobmanager():
        from sage.jobmanager.job_manager import JobManager
        jobmanager = JobManager(enable_daemon=True, daemon_host="127.0.0.1", daemon_port=19003)
        jobmanager.run_forever()
    
    # 在单独线程中启动JobManager
    jm_thread = threading.Thread(target=start_jobmanager, daemon=True)
    jm_thread.start()
    
    # 等待JobManager启动
    time.sleep(3)
    print("   JobManager started")
    
    # 2. 创建RemoteEnvironment并提交
    print("2. Creating and submitting RemoteEnvironment...")
    try:
        from sage.api.remote_environment import RemoteEnvironment
        
        # 创建远程环境
        remote_env = RemoteEnvironment(
            name="test_submission",
            config={"test_param": "test_value", "debug": True},
            host="127.0.0.1",
            port=19003
        )
        
        print(f"   Created RemoteEnvironment: {remote_env}")
        
        # 先测试健康检查
        health = remote_env.health_check()
        print(f"   Health check: {health.get('status', 'unknown')}")
        
        if health.get("status") != "success":
            print("   ❌ JobManager不健康，无法继续测试")
            return False
        
        # 提交环境
        print("   Submitting environment...")
        job_uuid = remote_env.submit()
        print(f"   ✅ Environment submitted with UUID: {job_uuid}")
        
        # 3. 检查作业状态
        print("3. Checking job status...")
        time.sleep(1)  # 等待一下让作业开始运行
        
        status = remote_env.get_job_status()
        print(f"   Job status: {status}")
        
        # 4. 停止作业
        print("4. Stopping job...")
        stop_result = remote_env.stop()
        print(f"   Stop result: {stop_result}")
        
        print("\n✅ 端到端流程测试成功!")
        return True
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_serialization_only():
    """只测试序列化部分（不需要JobManager）"""
    print("\n=== 测试序列化部分 ===")
    
    try:
        from sage.api.remote_environment import RemoteEnvironment
        from sage.utils.serialization.dill_serializer import trim_object_for_ray, serialize_object, deserialize_object
        
        # 创建环境
        env = RemoteEnvironment("test_serialization", {"key": "value"})
        print(f"Created environment: {env}")
        
        # Trim
        trimmed = trim_object_for_ray(env)
        print(f"Trimmed: {type(trimmed)}")
        
        # Serialize
        serialized = serialize_object(trimmed)
        print(f"Serialized: {len(serialized)} bytes")
        
        # Deserialize
        deserialized = deserialize_object(serialized)
        print(f"Deserialized: {type(deserialized)}, name={getattr(deserialized, 'name', 'N/A')}")
        
        print("✅ 序列化测试成功!")
        return True
        
    except Exception as e:
        print(f"❌ 序列化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        # 先测试序列化
        serialization_ok = test_serialization_only()
        
        if serialization_ok:
            # 如果序列化OK，测试端到端流程
            end_to_end_ok = test_remote_submission_flow()
            
            if end_to_end_ok:
                print("\n🎉 所有测试都通过了!")
                sys.exit(0)
            else:
                print("\n⚠️  序列化测试通过，但端到端测试失败")
                sys.exit(1)
        else:
            print("\n❌ 序列化测试失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
