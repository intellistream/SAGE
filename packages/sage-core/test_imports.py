#!/usr/bin/env python3
"""
测试修复后的 SAGE 导入
"""

def test_sage_imports():
    """测试各种 SAGE 模块的导入"""
    print("🧪 测试 SAGE 导入修复")
    print("=" * 50)
    
    # 1. 测试基础 sage 导入
    try:
        import sage
        print("✅ sage 包导入成功")
    except ImportError as e:
        print(f"❌ sage 包导入失败: {e}")
        return False
    
    # 2. 测试兼容性层
    try:
        from sage.core.api.compatibility import CompatibilityLayer
        print("✅ 兼容性层导入成功")
        
        # 检查闭源模块状态
        status = CompatibilityLayer.check_closed_source_availability()
        print("📊 闭源模块状态:")
        for module, state in status.items():
            icon = "✅" if state == "available" else "🔄"
            print(f"   {icon} {module}: {state}")
            
    except ImportError as e:
        print(f"❌ 兼容性层导入失败: {e}")
    
    # 3. 测试核心 API 导入
    try:
        from sage.core.api.local_environment import LocalEnvironment
        print("✅ LocalEnvironment 导入成功")
    except ImportError as e:
        print(f"❌ LocalEnvironment 导入失败: {e}")
        print(f"   错误详情: {e}")
        return False
    
    # 4. 测试 BaseEnvironment 导入
    try:
        from sage.core.api.base_environment import BaseEnvironment
        print("✅ BaseEnvironment 导入成功")
    except ImportError as e:
        print(f"❌ BaseEnvironment 导入失败: {e}")
        print(f"   错误详情: {e}")
        return False
    
    # 5. 测试创建环境实例
    try:
        env = LocalEnvironment()
        print("✅ LocalEnvironment 实例创建成功")
        print(f"   环境类型: {type(env).__name__}")
    except Exception as e:
        print(f"⚠️ LocalEnvironment 实例创建失败: {e}")
        # 这可能不是致命错误，继续测试
    
    print("\n🎉 导入测试完成！")
    return True

if __name__ == "__main__":
    test_sage_imports()
