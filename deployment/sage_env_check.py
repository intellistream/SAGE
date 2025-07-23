#!/usr/bin/env python3
"""
SAGE环境检查工具

用于检查本地和远程环境的兼容性，并提供对齐建议
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

try:
    from sage_core.api.remote_environment import RemoteEnvironment
    from sage_utils.logging_utils import configure_logging
    import logging
except ImportError as e:
    print(f"导入SAGE模块失败: {e}")
    print("请确保您在正确的Python环境中运行此脚本")
    sys.exit(1)


def print_section(title: str):
    """打印节标题"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """打印子节标题"""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


def format_env_info(env_info: Dict[str, Any], title: str):
    """格式化环境信息显示"""
    print(f"\n{title}:")
    print(f"  Python版本: {env_info.get('python_version', 'N/A').split()[0] if env_info.get('python_version') else 'N/A'}")
    print(f"  Python路径: {env_info.get('python_executable', 'N/A')}")
    print(f"  平台: {env_info.get('platform', 'N/A')}")
    
    venv = env_info.get('virtual_env') or env_info.get('conda_env')
    print(f"  虚拟环境: {venv or 'N/A'}")
    
    print(f"  工作目录: {env_info.get('working_directory', 'N/A')}")
    print(f"  Ray版本: {env_info.get('ray_version', 'N/A')}")
    print(f"  Dill版本: {env_info.get('dill_version', 'N/A')}")


def check_environment(host: str, port: int, verbose: bool = False):
    """执行环境检查"""
    print_section("SAGE环境兼容性检查")
    
    # 创建RemoteEnvironment
    print("创建RemoteEnvironment连接...")
    try:
        env = RemoteEnvironment("env_check_tool", host=host, port=port)
        print(f"✓ 连接到 {host}:{port}")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False
    
    # 健康检查
    print_subsection("连接健康检查")
    try:
        health = env.health_check()
        if health.get("status") == "success":
            print("✓ 远程JobManager连接正常")
        else:
            print(f"⚠ 远程JobManager状态异常: {health.get('message')}")
            if not verbose:
                print("使用 -v 选项获取详细信息")
    except Exception as e:
        print(f"✗ 健康检查失败: {e}")
        return False
    
    # 环境兼容性检查
    print_subsection("环境兼容性分析")
    try:
        compatibility = env.check_environment_compatibility(detailed=True)
        
        # 显示兼容性结果
        if compatibility["compatible"]:
            if compatibility["warnings"]:
                print("⚠ 环境基本兼容，但存在警告")
            else:
                print("✓ 环境完全兼容")
        else:
            print("✗ 环境不兼容")
        
        # 显示问题
        if compatibility["errors"]:
            print(f"\n错误 ({len(compatibility['errors'])}):")
            for i, error in enumerate(compatibility["errors"], 1):
                print(f"  {i}. {error}")
        
        if compatibility["warnings"]:
            print(f"\n警告 ({len(compatibility['warnings'])}):")
            for i, warning in enumerate(compatibility["warnings"], 1):
                print(f"  {i}. {warning}")
        
        # 详细环境信息
        if verbose and "local_env" in compatibility:
            print_subsection("详细环境信息")
            format_env_info(compatibility["local_env"], "本地环境")
            format_env_info(compatibility["remote_env"], "远程环境")
        
        return compatibility
        
    except Exception as e:
        print(f"✗ 兼容性检查失败: {e}")
        return False


def align_environment(host: str, port: int, force: bool = False):
    """尝试环境对齐"""
    print_section("环境对齐")
    
    try:
        env = RemoteEnvironment("env_align_tool", host=host, port=port)
        
        print("执行环境对齐...")
        result = env.align_environment(force=force)
        
        if result["status"] == "success":
            if result["alignment_performed"]:
                print("✓ 环境对齐已启动")
                print("注意: 如果需要重启Python进程，请按提示操作")
            else:
                print("✓ 环境已经兼容，无需对齐")
            return True
        else:
            print(f"⚠ 环境对齐失败: {result['message']}")
            
            if "compatibility_issues" in result:
                issues = result["compatibility_issues"]
                if issues.get("errors"):
                    print("未解决的错误:")
                    for error in issues["errors"]:
                        print(f"  - {error}")
                if issues.get("warnings"):
                    print("未解决的警告:")
                    for warning in issues["warnings"]:
                        print(f"  - {warning}")
            
            return False
            
    except Exception as e:
        print(f"✗ 环境对齐过程失败: {e}")
        return False


def show_suggestions(compatibility_result):
    """显示修复建议"""
    if not compatibility_result or compatibility_result == True:
        return
    
    print_section("修复建议")
    
    all_issues = compatibility_result.get("errors", []) + compatibility_result.get("warnings", [])
    
    suggestions = []
    
    for issue in all_issues:
        if "Python version mismatch" in issue:
            suggestions.append("• 考虑使用pyenv或conda管理Python版本，确保本地和远程环境使用相同版本")
            
        elif "ray_version mismatch" in issue:
            suggestions.append("• 统一Ray版本: pip install ray==<远程版本>")
            
        elif "dill_version mismatch" in issue:
            suggestions.append("• 统一Dill版本: pip install dill==<远程版本>")
            
        elif "Virtual environment mismatch" in issue:
            suggestions.append("• 检查虚拟环境配置，考虑使用相同的环境名称和路径")
    
    if not suggestions:
        suggestions = [
            "• 确保本地和远程环境使用相同的Python版本",
            "• 检查关键依赖包(ray, dill)的版本一致性", 
            "• 考虑使用Docker容器确保环境完全一致"
        ]
    
    for suggestion in set(suggestions):  # 去重
        print(suggestion)
    
    print(f"\n如需更多帮助，请查看文档: docs/multi_tenant_environment_solution.md")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SAGE环境检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s check                    # 基本环境检查
  %(prog)s check -v                 # 详细环境检查
  %(prog)s check --host 192.168.1.100 --port 19002   # 自定义连接
  %(prog)s align                    # 尝试环境对齐
  %(prog)s align --force            # 强制环境对齐
        """
    )
    
    parser.add_argument("command", choices=["check", "align"], 
                       help="要执行的操作")
    parser.add_argument("--host", default="127.0.0.1",
                       help="JobManager守护进程主机地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=19001,
                       help="JobManager守护进程端口 (默认: 19001)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="显示详细信息")
    parser.add_argument("--force", action="store_true",
                       help="强制执行对齐 (仅用于align命令)")
    parser.add_argument("--quiet", action="store_true",
                       help="减少输出信息")
    
    args = parser.parse_args()
    
    # 配置日志
    if not args.quiet:
        configure_logging(level=logging.INFO if args.verbose else logging.WARNING)
    
    try:
        if args.command == "check":
            compatibility = check_environment(args.host, args.port, args.verbose)
            if compatibility and compatibility != True:
                show_suggestions(compatibility)
            
            return 0 if compatibility else 1
            
        elif args.command == "align":
            success = align_environment(args.host, args.port, args.force)
            return 0 if success else 1
            
    except KeyboardInterrupt:
        print("\n操作被用户取消")
        return 130
    except Exception as e:
        print(f"\n发生未预期的错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
