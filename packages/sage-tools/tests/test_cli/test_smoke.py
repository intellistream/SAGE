#!/usr/bin/env python3
"""
SAGE CLI 冒烟测试 (Smoke Test)

这是一个轻量级的快速验证脚本，只测试最关键的核心功能：
1. CLI能否正常启动
2. 核心命令是否可访问
3. 基本功能是否工作

与 test_commands_full.py 的区别：
- Smoke Test: 快速验证，2-3分钟，关键路径
- Full Test: 详细测试，可能10-15分钟，覆盖所有功能
"""

import subprocess
import sys
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    current = Path(__file__).parent
    while current.parent != current:
        if (current / "packages").exists() and (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path(__file__).parent.parent.parent.parent.parent

def run_smoke_test(cmd_list, test_name, timeout=20):
    """运行单个冒烟测试"""
    print(f"🔥 {test_name}")
    try:
        # 状态检查需要更长时间
        test_timeout = 30 if "状态" in test_name else timeout
        result = subprocess.run(
            cmd_list, 
            capture_output=True, 
            text=True, 
            timeout=test_timeout,
            cwd=get_project_root()
        )
        
        if result.returncode == 0:
            print("  ✅ 通过")
            return True
        else:
            print(f"  ❌ 失败 (退出码: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ 超时 (>{test_timeout}s)")
        return False
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return False

def main():
    """冒烟测试主函数 - 只测试最关键的功能"""
    print("� SAGE CLI 冒烟测试")
    print("目标：快速验证核心功能是否可用\n")
    
    # 只测试最关键的功能路径
    critical_tests = [
        # 1. CLI基础功能
        ([sys.executable, "-m", "sage.tools.cli", "--help"], "CLI启动"),
        ([sys.executable, "-m", "sage.tools.cli", "version"], "版本命令"),
        
        # 2. 最重要的dev命令
        ([sys.executable, "-m", "sage.tools.cli", "dev", "--help"], "dev命令"),
        ([sys.executable, "-m", "sage.tools.cli", "dev", "status"], "状态检查"),
        
        # 3. 向后兼容性
        (["sage-dev", "--help"], "向后兼容性"),
        
        # 4. 关键诊断功能  
        ([sys.executable, "-m", "sage.tools.cli", "doctor"], "系统诊断"),
    ]
    
    passed = 0
    total = len(critical_tests)
    
    for cmd_list, desc in critical_tests:
        if run_smoke_test(cmd_list, desc):
            passed += 1
    
    print(f"\n📊 冒烟测试结果:")
    print(f"✅ 通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 冒烟测试通过 - 核心功能正常")
        return True
    else:
        print("🚨 冒烟测试失败 - 需要立即修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
