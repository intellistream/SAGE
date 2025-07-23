#!/usr/bin/env python3
"""
测试RemoteEnvironment的日志软链接功能
"""

import os
import sys
import time
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_remote_environment_log_symlink():
    """测试RemoteEnvironment的日志软链接功能"""
    print("=== RemoteEnvironment 日志软链接测试 ===\n")
    
    try:
        from sage_core.api.remote_environment import RemoteEnvironment
        
        # 1. 创建RemoteEnvironment实例
        print("1. 创建RemoteEnvironment实例...")
        env = RemoteEnvironment(name="test_remote_log", host="127.0.0.1", port=19001)
        
        # 2. 检查初始软链接状态
        print("2. 检查初始软链接状态...")
        symlink_status = env.get_log_symlink_status()
        print(f"   软链接状态: {symlink_status}")
        
        # 3. 检查软链接文件是否存在
        project_root = Path(__file__).parent
        symlink_path = project_root / "logs" / "remote_jobmanager_latest"
        
        print(f"3. 检查软链接文件: {symlink_path}")
        if symlink_path.exists():
            if symlink_path.is_symlink():
                target = symlink_path.resolve()
                print(f"   软链接存在，指向: {target}")
                print(f"   目标是否存在: {target.exists()}")
            else:
                print(f"   路径存在但不是软链接")
        else:
            print(f"   软链接不存在")
        
        # 4. 尝试获取远程信息（如果远程JobManager运行的话）
        print("4. 尝试获取远程JobManager信息...")
        try:
            remote_info = env.get_remote_info()
            print(f"   远程信息: {remote_info}")
        except Exception as e:
            print(f"   无法连接到远程JobManager: {e}")
        
        # 5. 测试健康检查
        print("5. 测试健康检查...")
        try:
            health = env.health_check()
            print(f"   健康检查结果: {health}")
        except Exception as e:
            print(f"   健康检查失败: {e}")
            
        print("\n=== 测试完成 ===")
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保SAGE项目正确安装")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

def check_logs_directory():
    """检查logs目录结构"""
    print("\n=== 检查logs目录结构 ===")
    
    project_root = Path(__file__).parent
    logs_dir = project_root / "logs"
    
    print(f"项目根目录: {project_root}")
    print(f"logs目录: {logs_dir}")
    
    if logs_dir.exists():
        print("logs目录内容:")
        for item in sorted(logs_dir.iterdir()):
            if item.is_symlink():
                target = item.resolve()
                print(f"  {item.name} -> {target} (软链接)")
            elif item.is_dir():
                print(f"  {item.name}/ (目录)")
            else:
                print(f"  {item.name} (文件)")
    else:
        print("logs目录不存在")
    
    # 检查远程JobManager的日志目录
    remote_log_base = Path("/tmp/sage-jm")
    print(f"\n远程JobManager日志目录: {remote_log_base}")
    
    if remote_log_base.exists():
        print("远程日志目录内容:")
        for item in sorted(remote_log_base.iterdir()):
            if item.is_symlink():
                target = item.resolve()
                print(f"  {item.name} -> {target} (软链接)")
            elif item.is_dir():
                print(f"  {item.name}/ (目录)")
            else:
                print(f"  {item.name} (文件)")
    else:
        print("远程日志目录不存在")

if __name__ == "__main__":
    # 首先检查目录结构
    check_logs_directory()
    
    # 然后测试RemoteEnvironment
    test_remote_environment_log_symlink()
