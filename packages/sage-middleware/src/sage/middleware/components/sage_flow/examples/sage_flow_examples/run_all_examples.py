#!/usr/bin/env python3
"""
SAGE Flow 示例运行器
运行所有示例并报告结果
"""

import sys
import os
import subprocess
import time
from typing import List, Dict, Any
from pathlib import Path

# 示例文件列表
EXAMPLES = [
    "basic_stream_processing.py",
    "advanced_stream_processing.py",
    "performance_monitoring.py",
    # 添加更多示例
]

def run_example(example_file: str) -> Dict[str, Any]:
    """运行单个示例并返回结果"""
    result = {
        "file": example_file,
        "success": False,
        "output": "",
        "error": "",
        "duration": 0.0
    }
    
    start_time = time.time()
    try:
        cmd = [sys.executable, example_file]
        completed = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=30  # 30秒超时
        )
        duration = time.time() - start_time
        
        if completed.returncode == 0:
            result["success"] = True
            result["output"] = completed.stdout
        else:
            result["error"] = completed.stderr
            result["output"] = completed.stdout
            
        result["duration"] = duration
    except subprocess.TimeoutExpired:
        result["error"] = "Timeout after 30 seconds"
        result["duration"] = time.time() - start_time
    except Exception as e:
        result["error"] = str(e)
        result["duration"] = time.time() - start_time
    
    return result

def main():
    """主函数"""
    print("SAGE Flow 示例运行器")
    print("=" * 50)
    
    results: List[Dict[str, Any]] = []
    total_success = 0
    total_time = 0.0
    
    for example in EXAMPLES:
        print(f"\n运行 {example} ...")
        result = run_example(example)
        results.append(result)
        
        if result["success"]:
            total_success += 1
            print(f"✓ {example} 成功 (耗时: {result['duration']:.2f}s)")
        else:
            print(f"✗ {example} 失败: {result['error'][:100]}...")
        
        total_time += result["duration"]
    
    # 报告摘要
    print("\n" + "=" * 50)
    print("运行报告")
    print("=" * 50)
    print(f"总示例数: {len(EXAMPLES)}")
    print(f"成功数: {total_success}")
    print(f"失败数: {len(EXAMPLES) - total_success}")
    print(f"总耗时: {total_time:.2f}s")
    
    if total_success == len(EXAMPLES):
        print("🎉 所有示例运行成功!")
    else:
        print("⚠️  部分示例失败，请检查错误信息")
    
    # 详细输出 (可选)
    print("\n详细输出:")
    for result in results:
        print(f"\n--- {result['file']} ---")
        if result["success"]:
            print("成功")
            if result["output"]:
                print(result["output"][:200] + "..." if len(result["output"]) > 200 else result["output"])
        else:
            print(f"失败: {result['error']}")

if __name__ == "__main__":
    main()