#!/usr/bin/env python3
"""
SAGE 服务系统核心测试套件
运行所有保留的核心测试

测试覆盖范围：
1. 语法糖和服务调用功能
2. 服务任务基类和队列监听
3. mmap队列综合功能  
4. 多进程并发测试
5. 性能基准测试
6. Ray集成测试
"""

import os
import sys
import subprocess
import time
from typing import List, Tuple

def run_test(test_path: str, test_name: str) -> Tuple[bool, str, float]:
    """
    运行单个测试
    
    Returns:
        (success, output, duration)
    """
    print(f"\n{'='*60}")
    print(f"🧪 Running: {test_name}")
    print(f"📁 Path: {test_path}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {test_name} PASSED ({duration:.2f}s)")
            return True, result.stdout, duration
        else:
            print(f"❌ {test_name} FAILED ({duration:.2f}s)")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return False, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}", duration
            
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"⏰ {test_name} TIMEOUT ({duration:.2f}s)")
        return False, "Test timed out after 5 minutes", duration
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 {test_name} ERROR ({duration:.2f}s): {e}")
        return False, str(e), duration


def main():
    """运行所有核心测试"""
    print("🚀 SAGE 服务系统核心测试套件")
    print("=" * 80)
    
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # 定义核心测试列表
    core_tests = [
        # 服务调用功能测试
        ("tests/test_final_verification.py", "服务调用语法糖最终验证"),
        ("tests/test_service_task_base.py", "服务任务基类和队列监听"),
        
        # mmap队列测试
        ("sage_utils/mmap_queue/tests/test_comprehensive.py", "mmap队列综合功能"),
        ("sage_utils/mmap_queue/tests/test_multiprocess_concurrent.py", "多进程并发测试"),
        ("sage_utils/mmap_queue/tests/test_performance_benchmark.py", "性能基准测试"),
        ("sage_utils/mmap_queue/tests/test_ray_integration.py", "Ray集成测试"),
    ]
    
    # 运行测试
    results = []
    total_start_time = time.time()
    
    for test_path, test_name in core_tests:
        full_path = os.path.join(project_root, test_path)
        
        if not os.path.exists(full_path):
            print(f"⚠️  Test file not found: {full_path}")
            results.append((test_name, False, "File not found", 0))
            continue
        
        success, output, duration = run_test(full_path, test_name)
        results.append((test_name, success, output, duration))
    
    total_duration = time.time() - total_start_time
    
    # 输出测试总结
    print(f"\n{'='*80}")
    print("📊 测试结果总结")
    print(f"{'='*80}")
    
    passed_count = 0
    failed_count = 0
    
    for test_name, success, output, duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:<8} {test_name:<40} ({duration:.2f}s)")
        
        if success:
            passed_count += 1
        else:
            failed_count += 1
    
    print(f"\n{'='*80}")
    print(f"🎯 总体结果:")
    print(f"   ✅ 通过: {passed_count}/{len(results)} 测试")
    print(f"   ❌ 失败: {failed_count}/{len(results)} 测试")
    print(f"   ⏱️  总耗时: {total_duration:.2f}s")
    
    if passed_count == len(results):
        print(f"\n🎉 所有核心测试通过！SAGE 服务系统功能完整！")
        return 0
    else:
        print(f"\n⚠️  {failed_count} 个测试失败，请检查相关功能")
        
        # 显示失败的测试详情
        print(f"\n{'='*80}")
        print("❌ 失败测试详情:")
        print(f"{'='*80}")
        
        for test_name, success, output, duration in results:
            if not success:
                print(f"\n🔴 {test_name}:")
                print("-" * 40)
                print(output[:1000])  # 只显示前1000个字符
                if len(output) > 1000:
                    print("... (truncated)")
        
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
