#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 测试运行器
Test runner for SAGE high-performance memory-mapped queue test suite
"""

import os
import sys
import time
import multiprocessing
import subprocess
from typing import List, Dict, Any, Optional

# 添加上级目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.parent_dir = os.path.dirname(self.test_dir)
        self.results = []
        
    def run_test_module(self, module_name: str, description: str = None) -> Dict[str, Any]:
        """运行单个测试模块"""
        test_file = os.path.join(self.test_dir, f"{module_name}.py")
        
        if not os.path.exists(test_file):
            return {
                'module': module_name,
                'description': description or module_name,
                'success': False,
                'error': f"测试文件不存在: {test_file}",
                'duration': 0,
                'output': ""
            }
        
        print(f"\n{'='*60}")
        print(f"运行测试模块: {description or module_name}")
        print(f"文件: {test_file}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # 设置环境变量，添加SAGE项目根目录到PYTHONPATH
            env = os.environ.copy()
            sage_root = os.path.dirname(os.path.dirname(os.path.dirname(self.parent_dir)))
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{sage_root}:{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = sage_root
            # 运行测试模块
            result = subprocess.run(
                [sys.executable, test_file],
                cwd=self.parent_dir,  # 在父目录运行，确保路径正确
                capture_output=True,
                text=True,
                timeout=30,  # 30秒钟超时
                encoding='utf-8',  # 适配windows和Linux
                # 在Windows上可能需要添加 errors='replace' 来处理编码错误
                errors='replace'   # 添加这行，处理编码错误
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            # 打印输出
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            return {
                'module': module_name,
                'description': description or module_name,
                'success': success,
                'error': result.stderr if not success else None,
                'duration': duration,
                'output': result.stdout,
                'return_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'module': module_name,
                'description': description or module_name,
                'success': False,
                'error': f"测试超时 ({duration:.1f}s)",
                'duration': duration,
                'output': "",
                'return_code': -1
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                'module': module_name,
                'description': description or module_name,
                'success': False,
                'error': str(e),
                'duration': duration,
                'output': "",
                'return_code': -1
            }
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """运行所有测试"""
        
        # 定义测试模块列表
        test_modules = [
            # {
            #     'module': 'test_quick_validation',
            #     'description': '快速验证测试',
            #     'required': True
            # },
            # {
            #     'module': 'test_basic_functionality',
            #     'description': '基本功能测试',
            #     'required': True
            # },
            # {
            #     'module': 'test_safety',
            #     'description': '安全测试套件',
            #     'required': True
            # },
            {
                'module': 'test_performance_benchmark',
                'description': '性能基准测试',
                'required': False
            },
            {
                'module': 'test_comprehensive',
                'description': '综合测试套件',
                'required': False
            },
            {
                'module': 'test_multiprocess_concurrent',
                'description': '多进程并发测试',
                'required': False
            },
            {
                'module': 'test_ray_integration',
                'description': 'Ray Actor集成测试',
                'required': False
            }
        ]
        
        print("SAGE Memory-Mapped Queue 测试套件运行器")
        print("=" * 80)
        print(f"测试目录: {self.test_dir}")
        print(f"工作目录: {self.parent_dir}")
        print(f"总测试模块: {len(test_modules)}")
        print()
        
        results = []
        required_failures = 0
        
        for test_info in test_modules:
            result = self.run_test_module(
                test_info['module'],
                test_info['description']
            )
            
            result['required'] = test_info['required']
            results.append(result)
            
            # 打印单个测试结果
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            duration = f"{result['duration']:.1f}s"
            required_tag = "[必需]" if test_info['required'] else "[可选]"
            
            print(f"\n{status} {test_info['description']} {required_tag} ({duration})")
            
            if not result['success']:
                if test_info['required']:
                    required_failures += 1
                print(f"   错误: {result['error']}")
            
            # 如果是必需测试失败，询问是否继续
            if not result['success'] and test_info['required']:
                print(f"\n⚠️  必需测试 '{test_info['description']}' 失败!")
                response = input("是否继续运行其他测试？(y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("测试运行中止。")
                    break
        
        self.results = results
        return results
    
    def print_summary(self):
        """打印测试汇总"""
        if not self.results:
            print("没有测试结果可显示。")
            return
        
        print("\n" + "=" * 80)
        print("测试运行汇总")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        total_duration = sum(r['duration'] for r in self.results)
        
        required_tests = [r for r in self.results if r['required']]
        required_passed = sum(1 for r in required_tests if r['success'])
        required_failed = len(required_tests) - required_passed
        
        optional_tests = [r for r in self.results if not r['required']]
        optional_passed = sum(1 for r in optional_tests if r['success'])
        optional_failed = len(optional_tests) - optional_passed
        
        print(f"总体统计:")
        print(f"  总测试数: {total_tests}")
        print(f"  通过: {passed_tests}")
        print(f"  失败: {failed_tests}")
        print(f"  成功率: {passed_tests/total_tests*100:.1f}%")
        print(f"  总耗时: {total_duration:.1f}秒")
        print()
        
        print(f"必需测试:")
        print(f"  通过: {required_passed}/{len(required_tests)}")
        print(f"  失败: {required_failed}")
        print()
        
        print(f"可选测试:")
        print(f"  通过: {optional_passed}/{len(optional_tests)}")
        print(f"  失败: {optional_failed}")
        print()
        
        print("详细结果:")
        print("-" * 80)
        
        for result in self.results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            required_tag = "[必需]" if result['required'] else "[可选]"
            duration = f"{result['duration']:.1f}s"
            
            print(f"{status} {result['description']} {required_tag} ({duration})")
            
            if not result['success'] and result['error']:
                # 截断长错误信息
                error = result['error']
                if len(error) > 100:
                    error = error[:100] + "..."
                print(f"     错误: {error}")
        
        print("-" * 80)
        
        # 总体状态
        if required_failed == 0:
            if failed_tests == 0:
                print("🎉 所有测试都通过了! SAGE Memory-Mapped Queue 可以用于生产环境。")
            else:
                print(f"✅ 所有必需测试通过! 有 {optional_failed} 个可选测试失败，但不影响核心功能。")
        else:
            print(f"❌ 有 {required_failed} 个必需测试失败，需要修复后才能用于生产环境。")
        
        return required_failed == 0
    
    def save_results(self, filename: str = None):
        """保存测试结果到文件"""
        if not self.results:
            return
        
        if filename is None:
            timestamp = int(time.time())
            filename = f"test_results_{timestamp}.json"
        
        import json
        
        report_data = {
            'timestamp': time.time(),
            'test_suite': 'SAGE Memory-Mapped Queue Test Suite',
            'summary': {
                'total_tests': len(self.results),
                'passed_tests': sum(1 for r in self.results if r['success']),
                'failed_tests': sum(1 for r in self.results if not r['success']),
                'total_duration': sum(r['duration'] for r in self.results)
            },
            'results': self.results
        }
        
        filepath = os.path.join(self.test_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 测试结果已保存到: {filepath}")


def main():
    """主函数"""
    # 设置多进程启动方法
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass
    
    # 检查C库是否存在
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lib_files = ['ring_buffer.so', 'libring_buffer.so']
    lib_exists = any(os.path.exists(os.path.join(parent_dir, lib)) for lib in lib_files)
    
    if not lib_exists:
        print("❌ 错误: 找不到编译的C库文件!")
        print("请先运行以下命令编译C库:")
        print(f"  cd {parent_dir}")
        print("  ./build.sh")
        sys.exit(1)
    
    # 创建测试运行器并运行测试
    runner = TestRunner()
    
    try:
        results = runner.run_all_tests()
        success = runner.print_summary()
        runner.save_results()
        
        # 生成详细报告
        try:
            print("\n生成详细测试报告...")
            subprocess.run([
                sys.executable,
                os.path.join(runner.test_dir, 'generate_test_report.py')
            ], cwd=parent_dir)
        except Exception as e:
            print(f"生成详细报告失败: {e}")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断。")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试运行器异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
