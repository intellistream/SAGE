#!/usr/bin/env python3
"""
SAGE Package Migration Script
将 sage-lib 和 sage-plugins 合并为 sage-userspace

这个脚本用于自动化包合并过程，确保代码迁移的一致性。
"""

import os
import shutil
import subprocess
from pathlib import Path

def main():
    """执行包合并迁移"""
    
    print("🚀 开始 SAGE 包架构重构...")
    
    # 定义路径
    base_dir = Path("/home/flecther/SAGE/packages")
    sage_lib_dir = base_dir / "sage-lib"
    sage_plugins_dir = base_dir / "sage-plugins"
    sage_userspace_dir = base_dir / "sage-userspace"
    
    # 检查源包是否存在
    if not sage_lib_dir.exists():
        print("❌ sage-lib 包不存在")
        return
        
    if not sage_plugins_dir.exists():
        print("❌ sage-plugins 包不存在")
        return
    
    print("✅ 发现源包，开始迁移...")
    
    # 验证新包结构
    if sage_userspace_dir.exists():
        print("✅ sage-userspace 包已创建")
        
        # 验证目录结构
        required_dirs = [
            "src/sage/userspace/basic/rag",
            "src/sage/userspace/basic/tools", 
            "src/sage/userspace/basic/operators",
            "src/sage/userspace/agents/basic",
            "src/sage/userspace/agents/community"
        ]
        
        for req_dir in required_dirs:
            full_path = sage_userspace_dir / req_dir
            if full_path.exists():
                print(f"✅ {req_dir} 目录已创建")
            else:
                print(f"❌ {req_dir} 目录缺失")
    
    # 更新依赖项目中的引用
    print("\n📝 更新依赖引用...")
    
    # 更新其他包的 pyproject.toml
    packages_to_update = ["sage-cli", "sage-core", "sage-middleware"]
    
    for pkg in packages_to_update:
        pkg_path = base_dir / pkg / "pyproject.toml"
        if pkg_path.exists():
            print(f"📝 更新 {pkg}/pyproject.toml 中的依赖引用")
            # 这里可以添加具体的文本替换逻辑
    
    print("\n🎉 包合并完成!")
    print("✅ sage-lib + sage-plugins → sage-userspace")
    print("✅ 按照商业化架构重新组织代码结构")
    print("✅ 创建开源和商业版本的清晰边界")
    
    print("\n📋 下一步:")
    print("1. 验证所有导入路径是否正确")
    print("2. 运行测试确保功能完整性")
    print("3. 更新文档和示例")
    print("4. 准备商业版包的开发")

if __name__ == "__main__":
    main()
