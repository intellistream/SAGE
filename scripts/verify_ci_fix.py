#!/usr/bin/env python3
"""
验证 CI 依赖修复 - 检查关键依赖是否可用
"""

def check_cli_dependencies():
    """检查CLI依赖是否可用"""
    print("🔍 检查CLI依赖可用性...")
    
    cli_deps = ["typer", "rich"]
    missing = []
    
    for dep in cli_deps:
        try:
            __import__(dep)
            print(f"✅ {dep} 可导入")
        except ImportError as e:
            print(f"❌ {dep} 不可导入: {e}")
            missing.append(dep)
    
    if missing:
        print(f"\n⚠️ 缺失依赖: {missing}")
        print("这些依赖对于Examples测试是必需的")
        return False
    else:
        print("\n✅ 所有CLI依赖都可用！")
        return True

def check_issues_manager():
    """检查 Issues 管理器相关功能"""
    print("\n🔍 检查 Issues 管理器...")
    
    try:
        # 尝试导入相关模块
        from sage.tools.dev.issues.tests import IssuesTestSuite
        print("✅ IssuesTestSuite 可导入")
        
        # 创建实例（不运行实际测试）
        suite = IssuesTestSuite()
        print("✅ IssuesTestSuite 可实例化")
        
        return True
    except Exception as e:
        print(f"❌ Issues 管理器检查失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 SAGE CI 依赖验证\n")
    
    cli_ok = check_cli_dependencies()
    issues_ok = check_issues_manager()
    
    print("\n" + "="*50)
    
    if cli_ok and issues_ok:
        print("✅ 所有检查通过！CI修复应该生效")
        exit(0)
    else:
        print("❌ 某些检查失败，可能需要重新安装")
        exit(1)