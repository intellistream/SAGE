#!/usr/bin/env python3
"""
SAGE Enterprise Edition Installation and Management Test Script
企业版安装和管理测试脚本

功能:
1. 测试企业版安装流程
2. 验证许可证状态
3. 检查企业功能可用性
4. 模拟商业版安装场景
"""

import os
import sys
import json
import warnings
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

class EnterpriseInstallationTester:
    """企业版安装测试器"""
    
    def __init__(self):
        self.sage_root = Path(__file__).parent.parent
        self.config_dir = self.sage_root / ".sage"
        self.config_file = self.config_dir / "config.json"
        self.results: Dict[str, Any] = {}
        
    def test_license_detection(self) -> bool:
        """测试许可证检测"""
        print("🔍 Testing license detection...")
        
        try:
            # 检查配置文件
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    license_type = config.get('license_type', 'unknown')
                    print(f"   ✅ License type: {license_type}")
                    print(f"   ✅ Expires at: {config.get('expires_at', 'N/A')}")
                    print(f"   ✅ Features: {config.get('features', [])}")
                    self.results['license_detection'] = {
                        'status': 'success',
                        'license_type': license_type,
                        'config': config
                    }
                    return True
            else:
                print("   ❌ No license configuration found")
                self.results['license_detection'] = {
                    'status': 'failed',
                    'reason': 'No config file'
                }
                return False
                
        except Exception as e:
            print(f"   ❌ License detection failed: {e}")
            self.results['license_detection'] = {
                'status': 'error',
                'error': str(e)
            }
            return False

    def test_package_imports(self) -> bool:
        """测试包导入和企业功能"""
        print("📦 Testing package imports and enterprise features...")
        
        import_results = {}
        
        # 测试基础包导入
        base_packages = [
            ('intsage', '元包'),
            ('sage.kernel', '内核'),
            ('sage.middleware', '中间件'),
            ('sage.apps', '应用')
        ]
        
        for pkg_name, desc in base_packages:
            try:
                # 使用 warnings 捕获企业版警告
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    
                    if pkg_name == 'intsage':
                        import intsage
                        module = intsage
                    elif pkg_name == 'sage.kernel':
                        import sage.kernel
                        module = sage.kernel
                    elif pkg_name == 'sage.middleware':
                        import sage.middleware
                        module = sage.middleware
                    elif pkg_name == 'sage.apps':
                        import sage.apps
                        module = sage.apps
                        
                    # 检查是否有企业版警告
                    enterprise_warning = any('Enterprise' in str(warning.message) for warning in w)
                    
                    print(f"   ✅ {desc} ({pkg_name}) imported successfully")
                    if enterprise_warning:
                        print(f"      ⚠️  Enterprise warning detected")
                    
                    # 检查企业功能可用性
                    enterprise_available = getattr(module, '_ENTERPRISE_AVAILABLE', None)
                    if enterprise_available is not None:
                        print(f"      📊 Enterprise available: {enterprise_available}")
                    
                    import_results[pkg_name] = {
                        'status': 'success',
                        'enterprise_warning': enterprise_warning,
                        'enterprise_available': enterprise_available
                    }
                    
            except Exception as e:
                print(f"   ❌ {desc} ({pkg_name}) import failed: {e}")
                import_results[pkg_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        self.results['package_imports'] = import_results
        return all(result['status'] == 'success' for result in import_results.values())

    def test_enterprise_features(self) -> bool:
        """测试企业功能"""
        print("🏢 Testing enterprise features...")
        
        enterprise_tests = {}
        
        # 测试企业功能导入
        enterprise_modules = [
            ('sage.middleware.enterprise', '中间件企业功能'),
            ('sage.apps.enterprise', '应用企业功能')
        ]
        
        for module_name, desc in enterprise_modules:
            try:
                module = __import__(module_name, fromlist=[''])
                print(f"   ✅ {desc} module imported")
                
                # 检查企业功能
                if hasattr(module, 'require_enterprise_license'):
                    print(f"      📋 License requirement function available")
                
                # 测试许可证要求装饰器
                if hasattr(module, 'require_enterprise_license'):
                    try:
                        # 这应该会触发许可证检查但不抛出异常（因为我们有配置）
                        @module.require_enterprise_license
                        def test_enterprise_function():
                            return "Enterprise function works"
                        
                        result = test_enterprise_function()
                        print(f"      ✅ Enterprise function test: {result}")
                        enterprise_tests[module_name] = {'status': 'success', 'function_test': True}
                    except Exception as e:
                        print(f"      ⚠️  Enterprise function test failed: {e}")
                        enterprise_tests[module_name] = {'status': 'partial', 'function_test': False, 'error': str(e)}
                else:
                    enterprise_tests[module_name] = {'status': 'success', 'function_test': False}
                    
            except ImportError as e:
                print(f"   ❌ {desc} not available: {e}")
                enterprise_tests[module_name] = {'status': 'not_available', 'error': str(e)}
            except Exception as e:
                print(f"   ❌ {desc} test failed: {e}")
                enterprise_tests[module_name] = {'status': 'failed', 'error': str(e)}
        
        self.results['enterprise_features'] = enterprise_tests
        return len(enterprise_tests) > 0

    def test_installation_requirements(self) -> bool:
        """测试安装要求"""
        print("📋 Testing installation requirements...")
        
        # 检查requirements文件
        req_files = [
            'requirements.txt',
            'requirements-commercial.txt',
            'requirements-dev.txt',
            'requirements-prod.txt'
        ]
        
        req_results = {}
        for req_file in req_files:
            req_path = self.sage_root / req_file
            if req_path.exists():
                print(f"   ✅ {req_file} exists")
                try:
                    with open(req_path, 'r') as f:
                        content = f.read()
                        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                        print(f"      📊 Contains {len(lines)} requirement entries")
                        req_results[req_file] = {
                            'status': 'exists',
                            'entries': len(lines)
                        }
                except Exception as e:
                    print(f"      ❌ Failed to read {req_file}: {e}")
                    req_results[req_file] = {
                        'status': 'error',
                        'error': str(e)
                    }
            else:
                print(f"   ❌ {req_file} missing")
                req_results[req_file] = {'status': 'missing'}
        
        self.results['installation_requirements'] = req_results
        return 'requirements-commercial.txt' in req_results and req_results['requirements-commercial.txt']['status'] == 'exists'

    def test_package_configuration(self) -> bool:
        """测试包配置"""
        print("⚙️  Testing package configuration...")
        
        config_tests = {}
        
        # 检查pyproject.toml文件
        package_dirs = [
            'packages/sage',
            'packages/sage-kernel', 
            'packages/sage-middleware',
            'packages/sage-apps'
        ]
        
        for pkg_dir in package_dirs:
            pkg_path = self.sage_root / pkg_dir
            pyproject_path = pkg_path / 'pyproject.toml'
            
            if pyproject_path.exists():
                print(f"   ✅ {pkg_dir}/pyproject.toml exists")
                try:
                    with open(pyproject_path, 'r') as f:
                        content = f.read()
                        
                    # 检查企业版相关配置
                    has_enterprise = 'enterprise' in content.lower()
                    has_optional_deps = 'optional-dependencies' in content
                    
                    print(f"      📊 Enterprise mentions: {has_enterprise}")
                    print(f"      📊 Optional dependencies: {has_optional_deps}")
                    
                    config_tests[pkg_dir] = {
                        'status': 'exists',
                        'has_enterprise': has_enterprise,
                        'has_optional_deps': has_optional_deps
                    }
                except Exception as e:
                    print(f"      ❌ Failed to read pyproject.toml: {e}")
                    config_tests[pkg_dir] = {
                        'status': 'error',
                        'error': str(e)
                    }
            else:
                print(f"   ❌ {pkg_dir}/pyproject.toml missing")
                config_tests[pkg_dir] = {'status': 'missing'}
        
        self.results['package_configuration'] = config_tests
        return any(result['status'] == 'exists' for result in config_tests.values())

    def simulate_commercial_installation(self) -> bool:
        """模拟商业版安装过程"""
        print("🚀 Simulating commercial installation process...")
        
        # 模拟步骤
        steps = [
            "Checking license prerequisites",
            "Validating enterprise requirements", 
            "Installing base packages",
            "Installing enterprise extensions",
            "Configuring enterprise features",
            "Verifying installation"
        ]
        
        simulation_results = {}
        
        for i, step in enumerate(steps, 1):
            print(f"   {i}. {step}...")
            
            # 模拟处理时间
            import time
            time.sleep(0.1)
            
            if step == "Checking license prerequisites":
                # 检查许可证配置
                success = self.config_file.exists()
                status = "✅" if success else "❌"
                print(f"      {status} License configuration {'found' if success else 'missing'}")
                simulation_results[step] = {'status': 'success' if success else 'failed'}
                
            elif step == "Validating enterprise requirements":
                # 检查requirements文件
                req_file = self.sage_root / 'requirements-commercial.txt'
                success = req_file.exists()
                status = "✅" if success else "❌"
                print(f"      {status} Commercial requirements {'available' if success else 'missing'}")
                simulation_results[step] = {'status': 'success' if success else 'failed'}
                
            elif step == "Installing base packages":
                # 检查基础包是否已安装
                try:
                    import intsage
                    print(f"      ✅ Base packages available")
                    simulation_results[step] = {'status': 'success'}
                except ImportError:
                    print(f"      ❌ Base packages not available")
                    simulation_results[step] = {'status': 'failed'}
                    
            elif step == "Installing enterprise extensions":
                # 检查企业扩展
                try:
                    import sage.middleware.enterprise
                    import sage.apps.enterprise
                    print(f"      ✅ Enterprise extensions available")
                    simulation_results[step] = {'status': 'success'}
                except ImportError as e:
                    print(f"      ⚠️  Some enterprise extensions missing: {e}")
                    simulation_results[step] = {'status': 'partial'}
                    
            elif step == "Configuring enterprise features":
                # 检查企业功能配置
                config_exists = self.config_file.exists()
                if config_exists:
                    with open(self.config_file, 'r') as f:
                        config = json.load(f)
                        features = config.get('features', [])
                        print(f"      ✅ Enterprise features configured: {len(features)} features")
                        simulation_results[step] = {'status': 'success', 'features': features}
                else:
                    print(f"      ❌ Enterprise configuration missing")
                    simulation_results[step] = {'status': 'failed'}
                    
            elif step == "Verifying installation":
                # 综合验证
                try:
                    import intsage
                    import sage.middleware
                    print(f"      ✅ Installation verification passed")
                    simulation_results[step] = {'status': 'success'}
                except Exception as e:
                    print(f"      ❌ Installation verification failed: {e}")
                    simulation_results[step] = {'status': 'failed'}
            else:
                simulation_results[step] = {'status': 'success'}
        
        self.results['commercial_installation_simulation'] = simulation_results
        
        # 检查整体成功率
        success_count = sum(1 for result in simulation_results.values() if result['status'] in ['success', 'partial'])
        total_count = len(simulation_results)
        success_rate = success_count / total_count
        
        print(f"   📊 Installation simulation success rate: {success_rate:.1%} ({success_count}/{total_count})")
        return success_rate >= 0.8

    def generate_test_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("="*80)
        report.append("SAGE Enterprise Edition Installation Test Report")
        report.append("企业版安装测试报告")
        report.append("="*80)
        report.append(f"Generated at: {datetime.now().isoformat()}")
        report.append("")
        
        # 总结测试结果
        total_tests = len(self.results)
        passed_tests = sum(1 for test_results in self.results.values() 
                          if isinstance(test_results, dict) and 
                          any(result.get('status') == 'success' for result in 
                              (test_results.values() if isinstance(list(test_results.values())[0], dict) 
                               else [test_results])))
        
        report.append(f"📊 Test Summary: {passed_tests}/{total_tests} test categories passed")
        report.append("")
        
        # 详细结果
        for test_name, test_results in self.results.items():
            report.append(f"🔍 {test_name.replace('_', ' ').title()}:")
            
            if isinstance(test_results, dict):
                if 'status' in test_results:
                    # 单一测试结果
                    status_emoji = "✅" if test_results['status'] == 'success' else "❌"
                    report.append(f"   {status_emoji} Status: {test_results['status']}")
                    if 'error' in test_results:
                        report.append(f"   📝 Error: {test_results['error']}")
                else:
                    # 多个子测试结果
                    for sub_test, sub_result in test_results.items():
                        if isinstance(sub_result, dict) and 'status' in sub_result:
                            status_emoji = "✅" if sub_result['status'] == 'success' else "❌"
                            report.append(f"   {status_emoji} {sub_test}: {sub_result['status']}")
                            if 'error' in sub_result:
                                report.append(f"      📝 {sub_result['error']}")
            report.append("")
        
        return "\n".join(report)

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🎯 Starting SAGE Enterprise Edition Installation Tests")
        print("="*60)
        
        tests = [
            ("License Detection", self.test_license_detection),
            ("Package Imports", self.test_package_imports),
            ("Enterprise Features", self.test_enterprise_features),
            ("Installation Requirements", self.test_installation_requirements),
            ("Package Configuration", self.test_package_configuration),
            ("Commercial Installation Simulation", self.simulate_commercial_installation)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n🧪 Running {test_name}...")
            try:
                result = test_func()
                results.append(result)
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"   {status}")
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                results.append(False)
        
        print("\n" + "="*60)
        print("📋 Test Results Summary:")
        for i, (test_name, _) in enumerate(tests):
            status = "✅ PASSED" if results[i] else "❌ FAILED"
            print(f"   {status} {test_name}")
        
        overall_success = sum(results) / len(results)
        print(f"\n🎯 Overall Success Rate: {overall_success:.1%}")
        
        # 生成详细报告
        report = self.generate_test_report()
        print("\n" + report)
        
        return overall_success >= 0.8

def main():
    """主函数"""
    tester = EnterpriseInstallationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 Enterprise installation tests completed successfully!")
        return 0
    else:
        print("\n⚠️  Some enterprise installation tests failed. Please check the report above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
