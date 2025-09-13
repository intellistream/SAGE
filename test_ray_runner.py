#!/usr/bin/env python3
"""
专门的Ray测试运行器
处理Ray测试的特殊需求和常见问题
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

def run_ray_test_with_timeout(test_file, test_name=None, timeout=30):
    """使用超时运行Ray测试"""
    
    cmd = [
        sys.executable, "-m", "pytest", 
        test_file,
        "-v", "--tb=short", 
        "-m", "ray or slow",
        "--timeout", str(timeout)
    ]
    
    if test_name:
        cmd.append(f"::{test_name}")
    
    print(f"运行命令: {' '.join(cmd)}")
    
    try:
        # 启动进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd="/home/shuhao/SAGE"
        )
        
        # 等待进程完成或超时
        try:
            stdout, _ = process.communicate(timeout=timeout + 10)
            return_code = process.returncode
            
            print("STDOUT:")
            print(stdout)
            
            return return_code == 0
            
        except subprocess.TimeoutExpired:
            print(f"测试超时 ({timeout + 10}秒)，终止进程...")
            process.kill()
            process.wait()
            return False
            
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return False

def cleanup_ray():
    """清理Ray进程"""
    try:
        subprocess.run(["ray", "stop"], timeout=10, capture_output=True)
        print("Ray清理完成")
    except:
        print("Ray清理可能有问题，继续...")

def main():
    """主函数"""
    
    # 测试文件列表
    test_files = [
        "packages/sage-kernel/tests/unit/core/test_comap_service_integration.py",
        "packages/sage-kernel/tests/unit/kernel/runtime/communication/queue/test_ray_actor_queue_communication.py", 
        "packages/sage-kernel/tests/unit/kernel/runtime/communication/queue/test_reference_passing_and_concurrency.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"测试文件: {test_file}")
        print(f"{'='*60}")
        
        # 清理Ray环境
        cleanup_ray()
        time.sleep(2)
        
        # 运行测试
        success = run_ray_test_with_timeout(test_file, timeout=20)
        results[test_file] = success
        
        print(f"结果: {'✅ PASSED' if success else '❌ FAILED'}")
        
        # 再次清理
        cleanup_ray()
        time.sleep(1)
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结:")
    print(f"{'='*60}")
    
    for test_file, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {test_file}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)