#!/usr/bin/env python3
"""
测试新的JobManager Actor架构的示例
"""

import sys
import time
from pathlib import Path

# 添加项目路径
SAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SAGE_ROOT))

def test_local_environment():
    """测试本地环境"""
    print("\n=== 测试本地环境 ===")
    
    from sage_core.api.local_environment import LocalStreamEnvironment
    
    # 创建本地环境
    env = LocalStreamEnvironment("test_local_env", config={"test": "local"})
    
    print(f"环境名称: {env.name}")
    print(f"平台: {env.platform}")
    
    # 测试jobmanager属性访问
    jobmanager = env.jobmanager
    print(f"JobManager类型: {type(jobmanager)}")
    print(f"JobManager是否本地: {jobmanager.is_local()}")
    print(f"JobManager是否Ray Actor: {jobmanager.is_ray_actor()}")
    
    # 测试调用jobmanager方法
    try:
        server_info = jobmanager.get_server_info()
        print(f"服务器信息: {server_info}")
    except Exception as e:
        print(f"获取服务器信息失败: {e}")
    
    print("✅ 本地环境测试完成")


def test_remote_environment():
    """测试远程环境"""
    print("\n=== 测试远程环境 ===")
    
    try:
        import ray
        
        # 初始化Ray（如果需要）
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
        
        from sage_core.api.remote_environment import RemoteStreamEnvironment
        
        # 创建远程环境
        env = RemoteStreamEnvironment("test_remote_env", config={
            "jobmanager_daemon_host": "127.0.0.1",
            "jobmanager_daemon_port": 19000
        })
        
        print(f"环境名称: {env.name}")
        print(f"平台: {env.platform}")
        
        # 尝试获取JobManager句柄
        # 注意：这需要Ray JobManager Daemon在运行
        try:
            jobmanager = env.jobmanager
            print(f"JobManager类型: {type(jobmanager)}")
            print(f"JobManager是否本地: {jobmanager.is_local()}")
            print(f"JobManager是否Ray Actor: {jobmanager.is_ray_actor()}")
            
            # 测试调用jobmanager方法
            server_info = jobmanager.get_server_info()
            print(f"服务器信息: {server_info}")
            
            print("✅ 远程环境测试完成")
            
        except Exception as e:
            print(f"⚠️ 远程环境测试失败（可能Ray JobManager Daemon未运行）: {e}")
            print("提示：请先运行 'python deployment/ray_jobmanager_daemon.py start'")
    
    except ImportError:
        print("⚠️ Ray未安装，跳过远程环境测试")


def test_actor_wrapper():
    """测试ActorWrapper的基本功能"""
    print("\n=== 测试ActorWrapper ===")
    
    from sage_utils.actor_wrapper import ActorWrapper
    from sage_jobmanager.job_manager import JobManager
    
    # 测试本地对象包装
    jobmanager = JobManager()
    wrapped = ActorWrapper(jobmanager)
    
    print(f"原始对象类型: {type(jobmanager)}")
    print(f"包装后类型: {type(wrapped)}")
    print(f"是否本地: {wrapped.is_local()}")
    print(f"是否Ray Actor: {wrapped.is_ray_actor()}")
    
    # 测试方法调用
    try:
        server_info = wrapped.get_server_info()
        print(f"通过wrapper调用方法成功: {list(server_info.keys())}")
    except Exception as e:
        print(f"通过wrapper调用方法失败: {e}")
    
    print("✅ ActorWrapper测试完成")


def main():
    """主函数"""
    print("SAGE JobManager Actor架构测试")
    print("=" * 50)
    
    # 基础组件测试
    test_actor_wrapper()
    
    # 本地环境测试
    test_local_environment()
    
    # 远程环境测试
    test_remote_environment()
    
    print("\n" + "=" * 50)
    print("所有测试完成")


if __name__ == "__main__":
    main()
