"""
Core模块测试运行脚本
根据issue要求，为sage-kernel的core模块创建完整的测试组织架构
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def get_project_root():
    """获取项目根目录"""
    current_dir = Path(__file__).parent
    # 向上查找pyproject.toml文件
    while current_dir.parent != current_dir:
        if (current_dir / "pyproject.toml").exists():
            return current_dir
        current_dir = current_dir.parent
    return Path(__file__).parent


def run_tests(test_path=None, coverage=True, verbose=True, markers=None, parallel=False):
    """运行测试"""
    project_root = get_project_root()
    os.chdir(project_root)
    
    # 基本命令
    cmd = ["python", "-m", "pytest"]
    
    # 测试路径
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/core/")
    
    # 详细输出
    if verbose:
        cmd.append("-v")
    
    # 覆盖率
    if coverage:
        cmd.extend([
            "--cov=src/sage/core",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/core",
            "--cov-report=xml:coverage-core.xml"
        ])
    
    # 标记过滤
    if markers:
        cmd.extend(["-m", markers])
    
    # 并行执行
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # 其他有用选项
    cmd.extend([
        "--strict-markers",
        "--strict-config", 
        "-ra"  # 显示所有测试结果摘要
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.run(cmd)


def run_specific_module_tests():
    """运行特定模块的测试"""
    modules = {
        "pipeline": "tests/core/test_pipeline.py",
        "function": "tests/core/function/",
        "operator": "tests/core/operator/",
        "service": "tests/core/service/",
        "api": "tests/core/api/"
    }
    
    print("Available test modules:")
    for key, path in modules.items():
        print(f"  {key}: {path}")
    
    while True:
        choice = input("\nEnter module name (or 'all' for all modules, 'quit' to exit): ").strip()
        
        if choice == 'quit':
            break
        elif choice == 'all':
            run_tests()
            break
        elif choice in modules:
            run_tests(modules[choice])
            break
        else:
            print(f"Invalid choice: {choice}")


def run_by_test_type():
    """按测试类型运行"""
    test_types = {
        "unit": "unit",
        "integration": "integration", 
        "slow": "slow"
    }
    
    print("Available test types:")
    for key, marker in test_types.items():
        print(f"  {key}: {marker}")
    
    choice = input("\nEnter test type: ").strip()
    
    if choice in test_types:
        run_tests(markers=test_types[choice])
    else:
        print(f"Invalid test type: {choice}")


def generate_test_report():
    """生成测试报告"""
    print("Generating comprehensive test report...")
    
    # 运行所有测试并生成覆盖率报告
    result = run_tests(
        coverage=True, 
        verbose=True, 
        parallel=False  # 避免并行执行时的输出混乱
    )
    
    if result.returncode == 0:
        print("\n" + "="*50)
        print("Test Report Generated Successfully!")
        print("="*50)
        print("Coverage HTML report: htmlcov/core/index.html")
        print("Coverage XML report: coverage-core.xml")
        print("Test results: Check terminal output above")
    else:
        print("\n" + "="*50)
        print("Tests Failed!")
        print("="*50)
        print("Please check the error messages above")
    
    return result.returncode


def check_test_structure():
    """检查测试结构是否符合issue要求"""
    project_root = get_project_root()
    core_tests_dir = project_root / "tests" / "core"
    
    required_structure = {
        "tests/core/test_pipeline.py": "Pipeline核心测试",
        "tests/core/function/test_base_function.py": "BaseFunction测试",
        "tests/core/function/test_comap_function.py": "CoMapFunction测试",
        "tests/core/function/test_sink_function.py": "SinkFunction测试",
        "tests/core/function/test_source_function.py": "SourceFunction测试",
        "tests/core/operator/test_base_operator.py": "BaseOperator测试",
        "tests/core/service/test_base_service.py": "BaseService测试",
        "tests/core/conftest.py": "测试配置文件"
    }
    
    print("Checking test structure compliance...")
    print("="*50)
    
    missing_files = []
    existing_files = []
    
    for test_file, description in required_structure.items():
        file_path = project_root / test_file
        if file_path.exists():
            existing_files.append((test_file, description))
            print(f"✓ {test_file} - {description}")
        else:
            missing_files.append((test_file, description))
            print(f"✗ {test_file} - {description} (MISSING)")
    
    print("\n" + "="*50)
    print(f"Structure Check Summary:")
    print(f"Existing files: {len(existing_files)}")
    print(f"Missing files: {len(missing_files)}")
    
    if missing_files:
        print("\nMissing files:")
        for file_path, description in missing_files:
            print(f"  - {file_path}")
        return False
    else:
        print("\n✓ All required test files are present!")
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SAGE Core Module Test Runner")
    parser.add_argument("--check-structure", action="store_true", 
                       help="Check if test structure complies with issue requirements")
    parser.add_argument("--module", choices=["pipeline", "function", "operator", "service", "api"],
                       help="Run tests for specific module")
    parser.add_argument("--type", choices=["unit", "integration", "slow"],
                       help="Run tests by type")
    parser.add_argument("--report", action="store_true",
                       help="Generate comprehensive test report")
    parser.add_argument("--no-coverage", action="store_true",
                       help="Run tests without coverage")
    parser.add_argument("--parallel", action="store_true",
                       help="Run tests in parallel")
    parser.add_argument("--interactive", action="store_true",
                       help="Interactive mode")
    
    args = parser.parse_args()
    
    if args.check_structure:
        success = check_test_structure()
        sys.exit(0 if success else 1)
    
    elif args.module:
        modules = {
            "pipeline": "tests/core/test_pipeline.py",
            "function": "tests/core/function/",
            "operator": "tests/core/operator/", 
            "service": "tests/core/service/",
            "api": "tests/core/api/"
        }
        result = run_tests(
            test_path=modules[args.module],
            coverage=not args.no_coverage,
            parallel=args.parallel
        )
        sys.exit(result.returncode)
    
    elif args.type:
        result = run_tests(
            markers=args.type,
            coverage=not args.no_coverage,
            parallel=args.parallel
        )
        sys.exit(result.returncode)
    
    elif args.report:
        exit_code = generate_test_report()
        sys.exit(exit_code)
    
    elif args.interactive:
        print("SAGE Core Module Test Runner - Interactive Mode")
        print("="*50)
        
        while True:
            print("\nOptions:")
            print("1. Check test structure")
            print("2. Run specific module tests")
            print("3. Run tests by type")
            print("4. Generate test report")
            print("5. Run all tests")
            print("6. Exit")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == "1":
                check_test_structure()
            elif choice == "2":
                run_specific_module_tests()
            elif choice == "3":
                run_by_test_type()
            elif choice == "4":
                generate_test_report()
            elif choice == "5":
                run_tests(coverage=not args.no_coverage, parallel=args.parallel)
            elif choice == "6":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
    
    else:
        # 默认运行所有core测试
        result = run_tests(
            coverage=not args.no_coverage,
            parallel=args.parallel
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
