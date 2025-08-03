#!/usr/bin/env python3
"""
SAGE 序列化模块测试套件
运行所有测试并生成报告
"""
import os
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def run_tests():
    """运行所有测试"""
    print("🚀 运行 SAGE 序列化模块测试套件")
    print("=" * 60)
    
    # 测试模块列表（排除向后兼容性测试）
    test_modules = [
        'test_exceptions.py',
        'test_config.py', 
        'test_preprocessor.py',
        'test_universal_serializer.py',
        'test_ray_trimmer.py',
        'test_main_api.py'
    ]
    
    total_passed = 0
    total_failed = 0
    failed_modules = []
    
    for module in test_modules:
        print(f"\n📋 运行测试: {module}")
        print("-" * 50)
        
        try:
            # 使用 pytest 运行单个测试模块
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                str(current_dir / module),
                '-v', '--tb=short'
            ], capture_output=True, text=True, cwd=str(project_root))
            
            if result.returncode == 0:
                print(f"✅ {module} 测试通过")
                # 尝试从输出中提取通过的测试数量
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line and '=====' in line:
                        import re
                        match = re.search(r'(\d+) passed', line)
                        if match:
                            total_passed += int(match.group(1))
                        break
            else:
                print(f"❌ {module} 测试失败")
                failed_modules.append(module)
                
                # 尝试从输出中提取失败的测试数量
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'failed' in line and 'passed' in line and '=====' in line:
                        import re
                        passed_match = re.search(r'(\d+) passed', line)
                        failed_match = re.search(r'(\d+) failed', line)
                        if passed_match:
                            total_passed += int(passed_match.group(1))
                        if failed_match:
                            total_failed += int(failed_match.group(1))
                        break
                
                # 显示错误信息的前几行
                if result.stdout:
                    error_lines = result.stdout.split('\n')
                    print("错误详情:")
                    for line in error_lines[-10:]:  # 显示最后10行
                        if line.strip():
                            print(f"  {line}")
                            
        except Exception as e:
            print(f"❌ 运行 {module} 时出错: {e}")
            failed_modules.append(module)
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("📊 测试报告")
    print("=" * 60)
    print(f"✅ 通过的测试: {total_passed}")
    print(f"❌ 失败的测试: {total_failed}")
    print(f"📁 测试模块总数: {len(test_modules)}")
    print(f"✨ 成功的模块: {len(test_modules) - len(failed_modules)}")
    
    if failed_modules:
        print(f"⚠️ 失败的模块: {', '.join(failed_modules)}")
        print("\n建议:")
        print("1. 检查失败测试的具体错误信息")
        print("2. 运行单个模块进行调试: python -m pytest test_<module>.py -v")
        print("3. 检查依赖是否正确安装")
    else:
        print("🎉 所有测试模块都通过了!")
    
    return len(failed_modules) == 0

def run_single_test(test_name):
    """运行单个测试模块"""
    if not test_name.endswith('.py'):
        test_name += '.py'
    
    test_file = current_dir / test_name
    if not test_file.exists():
        print(f"❌ 测试文件不存在: {test_name}")
        return False
    
    print(f"🧪 运行单个测试: {test_name}")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            str(test_file),
            '-v', '--tb=long'
        ], cwd=str(project_root))
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return False

def main():
    """主入口"""
    if len(sys.argv) > 1:
        # 运行指定的测试模块
        test_name = sys.argv[1]
        success = run_single_test(test_name)
        sys.exit(0 if success else 1)
    else:
        # 运行所有测试
        success = run_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
