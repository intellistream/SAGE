#!/usr/bin/env python3
"""
SAGE Quickstart Assistant (Internal Tool)
=========================================

⚠️  WARNING: 这是一个内部工具，不应该被用户直接调用！
     This is an internal tool and should NOT be called directly by users!

为quickstart.sh提供Python功能支持，
可以被bash脚本调用来执行复杂的任务。

This tool is designed to be called only by the quickstart.sh script
to provide enhanced functionality through Python.

Usage (Internal Only):
    python _quickstart_helper.py <command> [args...]

Commands:
    check-system              # 系统检查
    list-conda-envs          # 列出conda环境
    check-conda-env <name>   # 检查环境是否存在
    create-conda-env <name>  # 创建conda环境
    install-requirements     # 安装依赖
    test-installation        # 测试安装
"""

import sys
import json
from pathlib import Path

# 导入统一工具模块 - 修正相对路径  
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from unified_tools import logger, checker, conda_mgr, runner, file_mgr

def check_system():
    """系统检查命令"""
    # 注意: 不打印header，保持输出简洁，便于bash脚本解析
    
    # 基础检查 - 使用quiet模式避免输出干扰bash脚本
    issues = []
    if not checker.check_python_version((3, 10), quiet=True):
        issues.append("python")
    
    if not checker.check_command("git", quiet=True):
        issues.append("git")
        
    if not conda_mgr.is_conda_available(quiet=True):
        issues.append("conda")
    
    checker.check_disk_space(2.0, quiet=True)  # 开发环境需要更多空间
    
    if issues:
        print(f"ERRORS:{','.join(issues)}")
        return 1
    else:
        print("SUCCESS:all_checks_passed")
        return 0

def list_conda_envs():
    """列出conda环境"""
    envs = conda_mgr.list_environments()
    print(",".join(envs))
    return 0

def check_conda_env(env_name: str):
    """检查conda环境是否存在"""
    exists = conda_mgr.environment_exists(env_name)
    print("EXISTS" if exists else "NOT_EXISTS")
    return 0

def create_conda_env(env_name: str, python_version: str = "3.11"):
    """创建conda环境"""
    if conda_mgr.create_environment(env_name, python_version):
        print(f"SUCCESS:environment_{env_name}_created")
        return 0
    else:
        print(f"ERROR:failed_to_create_{env_name}")
        return 1

def install_requirements(project_root: str):
    """安装开发依赖"""
    logger.print_header("安装开发依赖")
    
    project_path = Path(project_root)
    
    # 查找requirements文件
    req_files = [
        project_path / "requirements.txt",
        project_path / "scripts" / "requirements" / "dev.txt",
        project_path / "scripts" / "requirements" / "base.txt"
    ]
    
    success_count = 0
    for req_file in req_files:
        if req_file.exists():
            if runner.run_pip_command(["-r", str(req_file)], f"安装 {req_file.name}"):
                success_count += 1
    
    if success_count > 0:
        print(f"SUCCESS:installed_{success_count}_requirement_files")
        return 0
    else:
        print("ERROR:no_requirements_installed")
        return 1

def test_installation():
    """测试安装"""
    logger.print_header("测试SAGE安装")
    
    try:
        # 测试基本导入
        import sage
        logger.print_success("✅ SAGE导入成功")
        
        # 测试CLI
        from sage.common.cli.main import app
        logger.print_success("✅ CLI工具可用")
        
        print("SUCCESS:installation_test_passed")
        return 0
    except Exception as e:
        logger.print_error(f"安装测试失败: {e}")
        print(f"ERROR:installation_test_failed:{e}")
        return 1

def get_system_info():
    """获取系统信息，返回JSON格式"""
    info = checker.get_system_info()
    print(json.dumps(info))
    return 0

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("ERROR:no_command_specified")
        return 1
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    # 命令分发
    try:
        if command == "check-system":
            return check_system()
        elif command == "list-conda-envs":
            return list_conda_envs()
        elif command == "check-conda-env":
            if not args:
                print("ERROR:env_name_required")
                return 1
            return check_conda_env(args[0])
        elif command == "create-conda-env":
            if not args:
                print("ERROR:env_name_required")
                return 1
            python_ver = args[1] if len(args) > 1 else "3.11"
            return create_conda_env(args[0], python_ver)
        elif command == "install-requirements":
            if not args:
                print("ERROR:project_root_required")
                return 1
            return install_requirements(args[0])
        elif command == "test-installation":
            return test_installation()
        elif command == "get-system-info":
            return get_system_info()
        else:
            print(f"ERROR:unknown_command:{command}")
            return 1
    except Exception as e:
        print(f"ERROR:command_failed:{e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())