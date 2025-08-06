#!/usr/bin/env python3
"""
SAGE Enterprise Edition Test Runner
企业版测试运行器 - 快速执行企业版验证测试
"""

import sys
import subprocess
from pathlib import Path

def run_test(script_name, description):
    """运行单个测试脚本"""
    print(f"\n🧪 {description}")
    print("=" * 50)
    
    script_path = Path(__file__).parent / script_name
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ 测试通过")
            if result.stdout.strip():
                print(result.stdout)
        else:
            print("❌ 测试失败")
            if result.stderr.strip():
                print(f"错误: {result.stderr}")
                
    except subprocess.TimeoutExpired:
        print("⏰ 测试超时")
    except Exception as e:
        print(f"💥 测试异常: {e}")

def main():
    """主测试函数"""
    print("🎯 SAGE Enterprise Edition Test Suite")
    print("=" * 60)
    
    # 快速验证测试
    run_test("enterprise_verification.py", "企业版基础验证")
    
    # 增强功能测试
    run_test("enhanced_commercial_manager.py", "企业版功能管理器")
    
    print(f"\n🏁 测试完成！")
    print("如需完整安装测试，请运行: python test_enterprise_installation.py")

if __name__ == "__main__":
    main()
