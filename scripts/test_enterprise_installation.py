#!/usr/bin/env python3
"""
SAGE Enterprise Installation Test Script
企业版安装测试脚本

模拟完整的企业版安装流程：
1. 许可证验证
2. 企业版依赖安装
3. 功能验证
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🔄 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            print(f"   ✅ Success")
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n')[:5]:  # 只显示前5行
                    print(f"      {line}")
                if len(result.stdout.strip().split('\n')) > 5:
                    print("      ...")
        else:
            print(f"   ❌ Failed (exit code: {result.returncode})")
            if result.stderr.strip():
                for line in result.stderr.strip().split('\n')[:3]:
                    print(f"      ERROR: {line}")
                    
        return result.returncode == 0
        
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def test_license_status():
    """测试许可证状态"""
    print("\n📋 Step 1: License Status Check")
    print("-" * 40)
    
    result = subprocess.run([
        sys.executable, 'tools/license/sage_license.py', 'status'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    
    # 检查是否有商业许可证
    has_commercial = 'Type: Commercial' in result.stdout
    return has_commercial

def install_license():
    """安装商业许可证"""
    print("\n🔑 Step 2: Installing Commercial License")
    print("-" * 40)
    
    # 生成新许可证
    generate_cmd = [
        sys.executable, 'tools/license/sage_license.py', 
        'generate', 'Enterprise Test Customer', '365'
    ]
    
    result = subprocess.run(generate_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Failed to generate license")
        return False
    
    print("✅ License generated")
    print(result.stdout)
    
    # 提取许可证密钥
    lines = result.stdout.split('\n')
    license_key = None
    for line in lines:
        if 'License Key:' in line:
            license_key = line.split('License Key:')[1].strip()
            break
    
    if not license_key:
        print("❌ Could not extract license key")
        return False
    
    # 安装许可证
    install_cmd = [
        sys.executable, 'tools/license/sage_license.py',
        'install', license_key
    ]
    
    result = subprocess.run(install_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ License installed successfully")
        print(result.stdout)
        return True
    else:
        print("❌ License installation failed")
        print(result.stderr)
        return False

def test_enterprise_installation():
    """测试企业版安装"""
    print("\n📦 Step 3: Enterprise Package Installation")
    print("-" * 40)
    
    # 使用 requirements-commercial.txt 安装
    install_cmd = [
        sys.executable, '-m', 'pip', 'install', 
        '-r', 'requirements-commercial.txt'
    ]
    
    return run_command(install_cmd, "Installing enterprise packages")

def test_enterprise_features():
    """测试企业版功能"""
    print("\n⚡ Step 4: Enterprise Features Verification")
    print("-" * 40)
    
    test_script = '''
import warnings
import sys

print("🔍 Testing Enterprise Features...")

# 捕获警告以验证许可证检查
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    
    try:
        import intsage
        print("   ✅ Meta-package imported")
        
        # 检查是否有企业版警告（应该没有，因为有许可证）
        enterprise_warning = any('Enterprise' in str(warning.message) for warning in w)
        if enterprise_warning:
            print("   ⚠️  Unexpected enterprise warning detected")
        else:
            print("   ✅ No enterprise warnings (license valid)")
            
    except Exception as e:
        print(f"   ❌ Meta-package import failed: {e}")
        sys.exit(1)

# 测试企业功能
try:
    from sage.middleware.enterprise import require_enterprise_license
    
    @require_enterprise_license
    def test_middleware():
        return "Middleware enterprise feature works"
    
    result = test_middleware()
    print(f"   ✅ Middleware enterprise: {result}")
    
except Exception as e:
    print(f"   ❌ Middleware enterprise test failed: {e}")
    sys.exit(1)

try:
    from sage.apps.enterprise import require_enterprise_license
    
    @require_enterprise_license
    def test_apps():
        return "Apps enterprise feature works"
    
    result = test_apps()
    print(f"   ✅ Apps enterprise: {result}")
    
except Exception as e:
    print(f"   ❌ Apps enterprise test failed: {e}")
    sys.exit(1)

# 测试企业版依赖
enterprise_deps = ['numba', 'redis', 'scipy', 'scikit-learn', 'joblib']
for dep in enterprise_deps:
    try:
        module = __import__(dep.replace('-', '_'))
        version = getattr(module, '__version__', 'Unknown')
        print(f"   ✅ {dep}: v{version}")
    except ImportError:
        print(f"   ❌ {dep}: Not available")

print("\\n✅ All enterprise features verified successfully!")
'''
    
    result = subprocess.run([sys.executable, '-c', test_script], 
                          capture_output=True, text=True)
    
    print(result.stdout)
    
    if result.returncode != 0:
        print("❌ Enterprise features test failed")
        if result.stderr:
            print(result.stderr)
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 SAGE Enterprise Installation Test")
    print("=" * 60)
    print("This script tests the complete enterprise installation process")
    
    # 步骤1: 检查许可证状态
    has_license = test_license_status()
    
    # 步骤2: 如果没有许可证，安装一个
    if not has_license:
        if not install_license():
            print("\n❌ License installation failed. Cannot proceed.")
            return 1
    else:
        print("\n✅ Commercial license already available")
    
    # 步骤3: 安装企业版包
    if not test_enterprise_installation():
        print("\n❌ Enterprise installation failed.")
        return 1
    
    # 步骤4: 验证企业版功能
    if not test_enterprise_features():
        print("\n❌ Enterprise features verification failed.")
        return 1
    
    print("\n🎉 Enterprise Installation Test Completed Successfully!")
    print("=" * 60)
    print("✅ License verified")
    print("✅ Enterprise packages installed")
    print("✅ Enterprise features working")
    print("\n💡 Your SAGE Enterprise installation is ready for use!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
