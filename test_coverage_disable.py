#!/usr/bin/env python3
"""
测试脚本：验证 coverage 禁用功能
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "packages/sage-tools/sage-dev-toolkit/src"))

from sage_dev_toolkit.tools.enhanced_test_runner import EnhancedTestRunner

def test_coverage_disabled():
    """测试禁用 coverage 功能"""
    
    print("=== 测试 Coverage 禁用功能 ===\n")
    
    # 创建项目根目录
    project_root = Path(__file__).parent
    
    print("1. 测试默认情况（coverage 禁用）...")
    runner_disabled = EnhancedTestRunner(str(project_root), enable_coverage=False)
    print(f"   Coverage 状态: {'启用' if runner_disabled.enable_coverage else '禁用'}")
    
    print("\n2. 测试启用 coverage...")
    runner_enabled = EnhancedTestRunner(str(project_root), enable_coverage=True)
    print(f"   Coverage 状态: {'启用' if runner_enabled.enable_coverage else '禁用'}")
    
    print("\n3. 测试向后兼容性（无 enable_coverage 参数）...")
    try:
        runner_default = EnhancedTestRunner(str(project_root))
        print(f"   Coverage 状态: {'启用' if runner_default.enable_coverage else '禁用'}")
        print("   ✅ 向后兼容性测试通过")
    except Exception as e:
        print(f"   ❌ 向后兼容性测试失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_coverage_disabled()
