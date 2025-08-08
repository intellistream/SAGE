#!/usr/bin/env python3
"""
测试 PyPI 上传功能的简单脚本
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🧪 测试: {description}")
    print(f"💻 命令: {' '.join(cmd)}")
    
    try:
        # 使用项目根目录作为工作目录，设置 PYTHONPATH
        project_root = Path(__file__).parent.parent.parent.parent
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent / "src")
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
        
        if result.returncode == 0:
            print(f"✅ 成功")
            if result.stdout.strip():
                print("输出:")
                print(result.stdout)
        else:
            print(f"❌ 失败 (退出码: {result.returncode})")
            if result.stderr.strip():
                print("错误:")
                print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 SAGE Dev Toolkit PyPI 功能测试")
    
    # 测试命令列表
    tests = [
        (["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "--help"], "PyPI 帮助命令"),
        (["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "list"], "列出可用包"),
        (["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "check"], "检查包配置"),
        (["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "build", "--help"], "构建帮助"),
        (["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "upload", "--help"], "上传帮助"),
        (["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "upload", "--dry-run", "intellistream-sage-kernel", "--skip-checks", "--skip-build"], "预演上传测试"),
    ]
    
    results = []
    for cmd, desc in tests:
        success = run_command(cmd, desc)
        results.append((desc, success))
    
    # 显示总结
    print("\n📊 测试总结:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for desc, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {desc}")
    
    print(f"\n🎯 通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("⚠️ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
