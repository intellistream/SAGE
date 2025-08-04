#!/usr/bin/env python3
"""
队列描述符引用传递和并发测试套件

统一运行所有相关测试：
1. 基础引用传递和并发测试
2. Ray Actor队列通信测试  
3. Python multiprocessing队列测试
4. 性能基准测试
"""

import sys
import os
import time
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/api-rework')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_test_module(module_name: str, test_function: str) -> bool:
    """运行测试模块中的特定测试函数"""
    try:
        print(f"\n{'='*60}")
        print(f"运行测试模块: {module_name}")
        print(f"{'='*60}")
        
        # 动态导入测试模块
        module = __import__(module_name, fromlist=[test_function])
        
        # 获取测试函数
        if hasattr(module, test_function):
            test_func = getattr(module, test_function)
            start_time = time.time()
            
            # 运行测试
            result = test_func()
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result:
                print(f"✅ {module_name} 测试通过 (耗时: {duration:.2f}秒)")
                return True
            else:
                print(f"❌ {module_name} 测试失败 (耗时: {duration:.2f}秒)")
                return False
        else:
            print(f"❌ 测试函数 {test_function} 在模块 {module_name} 中不存在")
            return False
            
    except ImportError as e:
        print(f"❌ 无法导入测试模块 {module_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ 运行测试模块 {module_name} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_prerequisites():
    """检查测试前提条件"""
    print("检查测试前提条件...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print(f"❌ Python版本过低: {sys.version_info}, 需要3.8+")
        return False
    else:
        print(f"✅ Python版本: {'.'.join(map(str, sys.version_info[:3]))}")
    
    # 检查必要的模块
    required_modules = [
        'threading',
        'multiprocessing', 
        'concurrent.futures',
        'queue'
    ]
    
    for module_name in required_modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name} 可用")
        except ImportError:
            print(f"❌ {module_name} 不可用")
            return False
    
    # 检查可选模块
    optional_modules = {
        'ray': 'Ray分布式计算框架',
        'sage_ext': 'SAGE扩展模块'
    }
    
    for module_name, description in optional_modules.items():
        try:
            __import__(module_name)
            print(f"✅ {module_name} ({description}) 可用")
        except ImportError:
            print(f"⚠️ {module_name} ({description}) 不可用，相关测试将跳过")
    
    return True


def run_basic_queue_tests():
    """运行基础队列测试"""
    print("\n" + "="*60)
    print("运行基础队列功能测试")
    print("="*60)
    
    try:
        from sage.runtime.communication.queue_descriptor import (
            create_python_queue,
            create_ray_queue,
            create_sage_queue
        )
        
        # 测试Python队列创建
        python_queue = PythonQueueDescriptor("basic_test_python")
        python_queue.put("test_item")
        item = python_queue.get()
        assert item == "test_item"
        print("✅ Python队列基础功能正常")
        
        # 测试multiprocessing队列创建
        mp_queue = PythonQueueDescriptor("basic_test_mp", use_multiprocessing=True)
        mp_queue.put("mp_test_item")
        mp_item = mp_queue.get()
        assert mp_item == "mp_test_item"
        print("✅ Multiprocessing队列基础功能正常")
        
        # 测试Ray队列创建（如果可用）
        try:
            ray_queue = create_ray_queue("basic_test_ray")
            print("✅ Ray队列创建成功")
        except Exception as e:
            print(f"⚠️ Ray队列创建失败: {e}")
        
        # 测试SAGE队列创建（如果可用）
        try:
            sage_queue = create_sage_queue("basic_test_sage")  
            print("✅ SAGE队列创建成功")
        except Exception as e:
            print(f"⚠️ SAGE队列创建失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础队列测试失败: {e}")
        return False


def generate_test_report(test_results: dict):
    """生成测试报告"""
    print("\n" + "="*60)
    print("测试结果报告")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result['success'])
    failed_tests = total_tests - passed_tests
    
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    print("\n详细结果:")
    for test_name, result in test_results.items():
        status = "✅ 通过" if result['success'] else "❌ 失败"
        duration = result.get('duration', 0)
        print(f"  {test_name}: {status} (耗时: {duration:.2f}秒)")
        
        if not result['success'] and 'error' in result:
            print(f"    错误: {result['error']}")
    
    # 生成报告文件
    report_file = Path("test_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 队列描述符测试报告\n\n")
        f.write(f"- 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- 总测试数: {total_tests}\n")
        f.write(f"- 通过: {passed_tests}\n")
        f.write(f"- 失败: {failed_tests}\n")
        f.write(f"- 成功率: {passed_tests/total_tests*100:.1f}%\n\n")
        
        f.write("## 详细结果\n\n")
        for test_name, result in test_results.items():
            status = "✅ 通过" if result['success'] else "❌ 失败"
            duration = result.get('duration', 0)
            f.write(f"### {test_name}\n")
            f.write(f"- 状态: {status}\n")
            f.write(f"- 耗时: {duration:.2f}秒\n")
            
            if not result['success'] and 'error' in result:
                f.write(f"- 错误: {result['error']}\n")
            f.write("\n")
    
    print(f"\n📄 测试报告已保存到: {report_file.absolute()}")
    
    return passed_tests == total_tests


def main():
    """主测试函数"""
    print("🚀 开始运行队列描述符引用传递和并发测试套件")
    print(f"Python版本: {sys.version}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查前提条件
    if not check_prerequisites():
        print("❌ 前提条件检查失败，退出测试")
        return False
    
    # 运行基础功能测试
    if not run_basic_queue_tests():
        print("❌ 基础功能测试失败，退出测试")
        return False
    
    # 定义要运行的测试
    test_modules = [
        {
            'name': '基础引用传递和并发测试',
            'module': 'test_reference_passing_and_concurrency',
            'function': 'run_all_tests'
        },
        {
            'name': 'Ray Actor队列通信测试',
            'module': 'test_ray_actor_queue_communication',
            'function': 'run_ray_actor_tests'
        }
    ]
    
    # 运行所有测试
    test_results = {}
    overall_start_time = time.time()
    
    for test_config in test_modules:
        test_name = test_config['name']
        module_name = test_config['module']
        function_name = test_config['function']
        
        start_time = time.time()
        try:
            success = run_test_module(module_name, function_name)
            end_time = time.time()
            
            test_results[test_name] = {
                'success': success,
                'duration': end_time - start_time
            }
        except Exception as e:
            end_time = time.time()
            test_results[test_name] = {
                'success': False,
                'duration': end_time - start_time,
                'error': str(e)
            }
    
    overall_end_time = time.time()
    overall_duration = overall_end_time - overall_start_time
    
    # 生成测试报告
    success = generate_test_report(test_results)
    
    print(f"\n🏁 测试套件完成，总耗时: {overall_duration:.2f}秒")
    
    if success:
        print("🎉 所有测试通过！队列描述符引用传递和并发功能正常。")
        return True
    else:
        print("💥 部分测试失败，请查看报告了解详情。")
        return False


if __name__ == "__main__":
    # 切换到测试目录
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    # 运行测试套件
    success = main()
    
    # 退出码
    sys.exit(0 if success else 1)
