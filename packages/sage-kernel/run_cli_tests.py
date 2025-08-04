#!/usr/bin/env python3
"""
Run CLI tests for sage-kernel package
根据issue要求运行CLI模块的完整测试套件
"""

import subprocess
import sys
import os
from pathlib import Path

def run_cli_tests():
    """运行CLI测试套件"""
    
    # 设置测试目录
    kernel_dir = Path(__file__).parent
    test_dir = kernel_dir / "tests" / "cli"
    
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    # 创建测试报告目录
    reports_dir = kernel_dir / "test_reports"
    reports_dir.mkdir(exist_ok=True)
    
    print("🚀 开始运行 sage-kernel CLI 测试套件")
    print(f"📁 测试目录: {test_dir}")
    print(f"📊 报告目录: {reports_dir}")
    print("=" * 60)
    
    # 配置pytest命令
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-c", str(kernel_dir / "pytest_cli.ini"),
        "--tb=short",
        "-x",  # 遇到第一个失败就停止
    ]
    
    # 运行单元测试
    print("🔬 运行单元测试...")
    unit_cmd = pytest_cmd + ["-m", "unit"]
    result = subprocess.run(unit_cmd, cwd=kernel_dir)
    
    if result.returncode != 0:
        print("❌ 单元测试失败")
        return False
    
    print("✅ 单元测试通过")
    print("-" * 40)
    
    # 运行集成测试
    print("🔗 运行集成测试...")
    integration_cmd = pytest_cmd + ["-m", "integration"]
    result = subprocess.run(integration_cmd, cwd=kernel_dir)
    
    if result.returncode != 0:
        print("⚠️  集成测试失败（可能需要外部依赖）")
    else:
        print("✅ 集成测试通过")
    
    print("-" * 40)
    
    # 运行完整测试套件并生成报告
    print("📋 生成完整测试报告...")
    full_cmd = pytest_cmd + [
        "--cov=sage.cli",
        "--cov-report=term",
        "--cov-report=html:test_reports/htmlcov",
        "--cov-report=xml:test_reports/coverage.xml",
        "--junitxml=test_reports/junit.xml"
    ]
    
    result = subprocess.run(full_cmd, cwd=kernel_dir)
    
    print("=" * 60)
    
    if result.returncode == 0:
        print("🎉 所有CLI测试完成！")
        print(f"📊 HTML报告: {reports_dir / 'htmlcov' / 'index.html'}")
        print(f"📄 XML报告: {reports_dir / 'coverage.xml'}")
        print(f"📋 JUnit报告: {reports_dir / 'junit.xml'}")
        return True
    else:
        print("❌ 测试运行过程中发现问题")
        return False


def print_test_summary():
    """打印测试摘要信息"""
    test_files = [
        "test_main.py - 主CLI入口点测试",
        "test_setup.py - CLI安装配置测试", 
        "test_head_manager.py - Head节点管理测试",
        "test_config_manager_new.py - 配置管理器测试",
        "test_job_new.py - 作业管理测试",
        "test_deploy_new.py - 系统部署测试",
        "test_worker_manager_new.py - Worker节点管理测试"
    ]
    
    print("\n📝 CLI测试文件覆盖:")
    for test_file in test_files:
        print(f"  ✓ {test_file}")
    
    print("\n🏷️  测试标记说明:")
    print("  • @pytest.mark.unit - 单元测试（快速、隔离）")
    print("  • @pytest.mark.integration - 集成测试（组件交互）") 
    print("  • @pytest.mark.slow - 耗时测试")
    print("  • @pytest.mark.external - 需要外部依赖的测试")
    
    print("\n🎯 测试目标:")
    print("  • 单元测试覆盖率 ≥ 80%")
    print("  • 集成测试覆盖率 ≥ 60%")
    print("  • 关键路径覆盖率 = 100%")


def main():
    """主函数"""
    print("🧪 SAGE CLI 测试套件")
    print("根据test-organization-planning-issue.md要求")
    print("完善 packages/sage-kernel/src/sage/cli 的测试覆盖")
    print("=" * 60)
    
    print_test_summary()
    
    print("\n" + "=" * 60)
    
    # 检查依赖
    try:
        import pytest
        import pytest_cov
        print("✅ 测试依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少测试依赖: {e}")
        print("请安装: pip install pytest pytest-cov pytest-mock")
        return 1
    
    # 运行测试
    success = run_cli_tests()
    
    if success:
        print("\n🎉 CLI测试套件执行成功！")
        print("\n📈 下一步:")
        print("  1. 查看测试报告确认覆盖率")
        print("  2. 集成到CI/CD管道")
        print("  3. 继续完善其他包的测试")
        return 0
    else:
        print("\n❌ CLI测试套件执行失败")
        print("请检查错误信息并修复问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
