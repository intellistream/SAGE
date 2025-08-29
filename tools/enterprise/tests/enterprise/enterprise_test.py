#!/usr/bin/env python3
"""
SAGE Enterprise Edition Test Suite
企业版测试套件 - 统一的企业版验证工具

用途：
- 许可证验证
- 企业版模块测试  
- 功能可用性检查
- 安装状态验证
"""

import sys
import subprocess
import warnings
import importlib
from pathlib import Path
from typing import Dict, List, Any

class EnterpriseValidator:
    """企业版验证器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.results = {}
        
    def test_license_status(self) -> Dict[str, Any]:
        """测试许可证状态"""
        print("📜 检查许可证状态...")
        
        try:
            result = subprocess.run([
                sys.executable, 
                str(self.project_root / "tools/license/sage_license.py"), 
                "status"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                return {
                    'status': 'success',
                    'message': '许可证有效',
                    'details': result.stdout.strip()
                }
            else:
                return {
                    'status': 'failed', 
                    'message': '许可证检查失败',
                    'error': result.stderr.strip()
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'许可证工具异常: {e}'
            }
    
    def test_enterprise_modules(self) -> Dict[str, Any]:
        """测试企业版模块导入"""
        print("🏢 检查企业版模块...")
        
        modules = [
            'sage.kernel.enterprise',
            'sage.middleware.enterprise', 
            'sage.apps.enterprise'
        ]
        
        results = {}
        all_success = True
        
        for module in modules:
            try:
                # 清除模块缓存
                if module in sys.modules:
                    del sys.modules[module]
                
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    importlib.import_module(module)
                    
                    # 检查是否有企业版警告
                    enterprise_warnings = [
                        warning for warning in w 
                        if 'Enterprise' in str(warning.message)
                    ]
                    
                    results[module] = {
                        'status': 'success',
                        'warnings': len(enterprise_warnings),
                        'warning_details': [str(w.message) for w in enterprise_warnings]
                    }
                    
            except ImportError as e:
                results[module] = {
                    'status': 'failed',
                    'error': str(e)
                }
                all_success = False
        
        return {
            'status': 'success' if all_success else 'partial',
            'modules': results,
            'summary': f"{len([r for r in results.values() if r['status'] == 'success'])}/{len(modules)} 模块正常"
        }
    
    def test_core_functionality(self) -> Dict[str, Any]:
        """测试核心功能"""
        print("🔧 检查核心功能...")
        
        try:
            # 测试基础sage模块
            import sage
            
            return {
                'status': 'success',
                'message': 'SAGE核心模块正常',
                'sage_path': str(sage.__file__),
                'available_attrs': [x for x in dir(sage) if not x.startswith('_')]
            }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'核心功能测试失败: {e}'
            }
    
    def run_full_test(self) -> Dict[str, Any]:
        """运行完整测试"""
        print("🎯 SAGE Enterprise Edition Validation")
        print("=" * 50)
        
        tests = [
            ('license', self.test_license_status),
            ('modules', self.test_enterprise_modules),
            ('core', self.test_core_functionality)
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
                status = results[test_name]['status']
                icon = "✅" if status == 'success' else "⚠️" if status == 'partial' else "❌"
                print(f"{icon} {test_name}: {results[test_name].get('message', status)}")
            except Exception as e:
                results[test_name] = {
                    'status': 'error',
                    'message': f'测试异常: {e}'
                }
                print(f"💥 {test_name}: 测试异常")
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """打印测试总结"""
        print("\n📊 测试总结")
        print("=" * 30)
        
        total_tests = len(results)
        successful_tests = len([r for r in results.values() if r['status'] == 'success'])
        
        print(f"总测试数: {total_tests}")
        print(f"成功测试: {successful_tests}")
        print(f"成功率: {successful_tests/total_tests*100:.1f}%")
        
        # 详细信息
        for test_name, result in results.items():
            status = result['status']
            if status != 'success':
                print(f"\n⚠️ {test_name} 问题:")
                if 'error' in result:
                    print(f"   错误: {result['error']}")
                if 'modules' in result:
                    for mod, mod_result in result['modules'].items():
                        if mod_result['status'] != 'success':
                            print(f"   {mod}: {mod_result.get('error', '未知错误')}")

def main():
    """主函数"""
    validator = EnterpriseValidator()
    
    try:
        results = validator.run_full_test()
        validator.print_summary(results)
        
        # 返回适当的退出码
        all_passed = all(r['status'] in ['success', 'partial'] for r in results.values())
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\n\n🛑 测试被用户取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
