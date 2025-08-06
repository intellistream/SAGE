#!/usr/bin/env python3
"""
SAGE Enterprise Installation Verification Script
企业版安装验证脚本

这个脚本用于验证SAGE企业版是否正确安装和配置
"""

import sys
import warnings
from pathlib import Path

def test_basic_installation():
    """测试基础安装"""
    print("🔍 测试基础安装...")
    
    results = {}
    
    # 测试meta-package
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import intsage
            
            # 检查是否有企业版警告
            enterprise_warning = any('Enterprise' in str(warning.message) for warning in w)
            results['meta_package'] = {
                'status': 'success',
                'warning_shown': enterprise_warning,
                'version': getattr(intsage, '__version__', 'Unknown')
            }
            print(f"   ✅ Meta-package (intsage): v{results['meta_package']['version']}")
            if enterprise_warning:
                print("      ⚠️  Enterprise license warning shown (expected)")
    except Exception as e:
        results['meta_package'] = {'status': 'failed', 'error': str(e)}
        print(f"   ❌ Meta-package import failed: {e}")
    
    # 测试namespace packages
    namespace_packages = [
        ('sage.kernel', '内核'),
        ('sage.middleware', '中间件'),
        ('sage.apps', '应用')
    ]
    
    for pkg_name, desc in namespace_packages:
        try:
            module = __import__(pkg_name, fromlist=[''])
            enterprise_available = getattr(module, '_ENTERPRISE_AVAILABLE', None)
            results[pkg_name] = {
                'status': 'success',
                'enterprise_available': enterprise_available
            }
            print(f"   ✅ {desc} ({pkg_name}): 可用")
            if enterprise_available is not None:
                print(f"      📊 Enterprise available: {enterprise_available}")
        except Exception as e:
            results[pkg_name] = {'status': 'failed', 'error': str(e)}
            print(f"   ❌ {desc} ({pkg_name}): 导入失败 - {e}")
    
    return results

def test_enterprise_dependencies():
    """测试企业版依赖"""
    print("\n🏢 测试企业版依赖...")
    
    # 核心企业版依赖
    enterprise_deps = {
        'numba': 'JIT编译和性能优化',
        'redis': 'Redis缓存和队列',
        'scipy': '科学计算库',
        'scikit-learn': '机器学习库',
        'joblib': '并行处理',
        'tqdm': '进度条显示',
        'psutil': '系统监控'
    }
    
    results = {}
    
    for pkg, desc in enterprise_deps.items():
        try:
            module = __import__(pkg.replace('-', '_'))
            version = getattr(module, '__version__', 'Unknown')
            results[pkg] = {'status': 'available', 'version': version}
            print(f"   ✅ {desc} ({pkg}): v{version}")
        except ImportError:
            results[pkg] = {'status': 'missing'}
            print(f"   ❌ {desc} ({pkg}): 未安装")
        except Exception as e:
            results[pkg] = {'status': 'error', 'error': str(e)}
            print(f"   ⚠️  {desc} ({pkg}): 导入错误 - {e}")
    
    return results

def test_enterprise_features():
    """测试企业版功能"""
    print("\n⚡ 测试企业版功能...")
    
    results = {}
    
    # 测试middleware企业功能
    try:
        from sage.middleware.enterprise import require_enterprise_license
        
        @require_enterprise_license
        def test_middleware_function():
            return "Middleware enterprise function works"
        
        result = test_middleware_function()
        results['middleware_enterprise'] = {'status': 'success', 'result': result}
        print(f"   ✅ Middleware企业功能: {result}")
    except Exception as e:
        results['middleware_enterprise'] = {'status': 'failed', 'error': str(e)}
        print(f"   ❌ Middleware企业功能测试失败: {e}")
    
    # 测试apps企业功能
    try:
        from sage.apps.enterprise import require_enterprise_license
        
        @require_enterprise_license
        def test_apps_function():
            return "Apps enterprise function works"
        
        result = test_apps_function()
        results['apps_enterprise'] = {'status': 'success', 'result': result}
        print(f"   ✅ Apps企业功能: {result}")
    except Exception as e:
        results['apps_enterprise'] = {'status': 'failed', 'error': str(e)}
        print(f"   ❌ Apps企业功能测试失败: {e}")
    
    # 测试numba加速
    try:
        import numba
        
        @numba.jit
        def fibonacci(n):
            if n <= 1:
                return n
            return fibonacci(n-1) + fibonacci(n-2)
        
        result = fibonacci(10)
        results['numba_acceleration'] = {'status': 'success', 'result': result}
        print(f"   ✅ Numba JIT加速: fibonacci(10) = {result}")
    except Exception as e:
        results['numba_acceleration'] = {'status': 'failed', 'error': str(e)}
        print(f"   ❌ Numba加速测试失败: {e}")
    
    return results

def test_license_configuration():
    """测试许可证配置"""
    print("\n📋 测试许可证配置...")
    
    results = {}
    
    # 检查许可证配置文件
    sage_root = Path.cwd()
    config_file = sage_root / '.sage' / 'config.json'
    
    if config_file.exists():
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            license_type = config.get('license_type', 'unknown')
            expires_at = config.get('expires_at', 'unknown')
            features = config.get('features', [])
            
            results['license_config'] = {
                'status': 'found',
                'license_type': license_type,
                'expires_at': expires_at,
                'features': features
            }
            
            print(f"   ✅ 许可证配置文件存在")
            print(f"   📋 许可证类型: {license_type}")
            print(f"   📅 过期时间: {expires_at}")
            print(f"   🎯 可用功能: {', '.join(features)}")
            
        except Exception as e:
            results['license_config'] = {'status': 'error', 'error': str(e)}
            print(f"   ❌ 许可证配置读取失败: {e}")
    else:
        results['license_config'] = {'status': 'missing'}
        print("   ❌ 许可证配置文件不存在")
    
    return results

def test_installation_requirements():
    """测试安装需求文件"""
    print("\n📦 测试安装需求文件...")
    
    results = {}
    
    req_files = [
        ('requirements.txt', '基础需求'),
        ('requirements-commercial.txt', '企业版需求'),
        ('requirements-dev.txt', '开发需求'),
        ('requirements-prod.txt', '生产需求')
    ]
    
    sage_root = Path.cwd()
    
    for req_file, desc in req_files:
        req_path = sage_root / req_file
        if req_path.exists():
            try:
                with open(req_path, 'r') as f:
                    content = f.read()
                lines = [line.strip() for line in content.split('\n') 
                        if line.strip() and not line.startswith('#')]
                
                results[req_file] = {'status': 'exists', 'entries': len(lines)}
                print(f"   ✅ {desc} ({req_file}): {len(lines)} 项依赖")
            except Exception as e:
                results[req_file] = {'status': 'error', 'error': str(e)}
                print(f"   ❌ {desc} ({req_file}): 读取失败 - {e}")
        else:
            results[req_file] = {'status': 'missing'}
            print(f"   ❌ {desc} ({req_file}): 文件不存在")
    
    return results

def generate_summary_report(all_results):
    """生成总结报告"""
    print("\n" + "="*60)
    print("📊 SAGE企业版安装验证总结报告")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n🔍 {category}:")
        
        if isinstance(results, dict):
            for test_name, result in results.items():
                total_tests += 1
                status = result.get('status', 'unknown')
                
                if status in ['success', 'available', 'exists', 'found']:
                    passed_tests += 1
                    emoji = "✅"
                elif status in ['partial']:
                    passed_tests += 0.5
                    emoji = "⚠️"
                else:
                    emoji = "❌"
                
                print(f"   {emoji} {test_name}: {status}")
                
                if 'error' in result:
                    print(f"      📝 错误: {result['error']}")
    
    print(f"\n📈 总体成功率: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests / total_tests >= 0.8:
        print("🎉 企业版安装验证通过！")
        return True
    else:
        print("⚠️  企业版安装存在问题，请检查上述失败项目")
        return False

def main():
    """主函数"""
    print("🚀 SAGE Enterprise Installation Verification")
    print("="*60)
    
    all_results = {}
    
    # 运行所有测试
    all_results['基础安装'] = test_basic_installation()
    all_results['企业版依赖'] = test_enterprise_dependencies()
    all_results['企业版功能'] = test_enterprise_features()
    all_results['许可证配置'] = test_license_configuration()
    all_results['安装需求文件'] = test_installation_requirements()
    
    # 生成总结报告
    success = generate_summary_report(all_results)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
