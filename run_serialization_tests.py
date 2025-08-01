#!/usr/bin/env python3
"""
序列化模块单元测试运行器

使用方法:
    python run_serialization_tests.py                    # 运行所有测试
    python run_serialization_tests.py --fast             # 快速测试（跳过慢速测试）
    python run_serialization_tests.py --module config    # 只测试config模块
    python run_serialization_tests.py --coverage         # 生成覆盖率报告
"""
import sys
import os
import subprocess
import argparse

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🔍 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=project_root)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - 成功")
            return True
        else:
            print(f"❌ {description} - 失败 (退出码: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ {description} - 异常: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='序列化模块测试运行器')
    parser.add_argument('--fast', action='store_true', help='快速测试（跳过慢速测试）')
    parser.add_argument('--module', type=str, help='只测试特定模块 (exceptions, config, preprocessor, universal_serializer, ray_trimmer, main_api, backward_compatibility)')
    parser.add_argument('--coverage', action='store_true', help='生成测试覆盖率报告')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    print("🚀 序列化模块单元测试")
    print("=" * 60)
    
    # 检查依赖
    print("🔍 检查测试依赖...")
    dependencies = ['pytest', 'dill']
    missing_deps = []
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} - 已安装")
        except ImportError:
            print(f"❌ {dep} - 未安装")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n请安装缺失的依赖: pip install {' '.join(missing_deps)}")
        return 1
    
    # 构建测试命令
    if args.module:
        # 测试特定模块
        test_path = f"tests/utils/serialization/test_{args.module}.py"
        if not os.path.exists(test_path):
            print(f"❌ 测试文件不存在: {test_path}")
            return 1
        cmd = f"python -m pytest {test_path}"
    else:
        # 测试所有模块
        cmd = "python -m pytest tests/utils/serialization/"
    
    # 添加选项
    if args.verbose:
        cmd += " -v"
    
    if args.fast:
        cmd += ' -m "not slow"'
    
    if args.coverage:
        cmd += " --cov=sage.utils.serialization --cov-report=html --cov-report=term-missing"
    
    # 运行测试
    success = run_command(cmd, "执行单元测试")
    
    if args.coverage and success:
        print("\n📊 覆盖率报告已生成到 htmlcov/ 目录")
        print("可以打开 htmlcov/index.html 查看详细报告")
    
    # 总结
    print("\n" + "=" * 60)
    if success:
        print("🎉 所有测试通过！")
        print("\n📚 更多信息:")
        print("  - 查看 tests/utils/serialization/ 目录了解测试结构")
        print("  - 查看 sage/utils/serialization/REFACTOR_GUIDE.md 了解模块说明")
        return 0
    else:
        print("❌ 测试失败，请查看上面的错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
