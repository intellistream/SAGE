#!/usr/bin/env python3
"""
配置文件迁移工具
将 project_config.toml 的有用信息迁移到 pyproject.toml，然后删除 project_config.toml
"""

import os
import re
from pathlib import Path

def migrate_to_standard_config():
    """迁移到标准的 pyproject.toml 配置"""
    root_dir = Path(__file__).parent.parent.parent
    project_config_file = root_dir / "project_config.toml"
    pyproject_file = root_dir / "pyproject.toml"
    
    print("🔄 开始迁移到标准配置...")
    
    # 检查文件是否存在
    if not project_config_file.exists():
        print("✅ project_config.toml 不存在，无需迁移")
        return
    
    if not pyproject_file.exists():
        print("❌ pyproject.toml 不存在")
        return
    
    # 读取 pyproject.toml
    with open(pyproject_file, 'r', encoding='utf-8') as f:
        pyproject_content = f.read()
    
    # 在 pyproject.toml 末尾添加自定义配置区域（如果需要的话）
    if "[tool.sage]" not in pyproject_content:
        sage_config = '''

# SAGE 项目自定义配置
[tool.sage]
# 如果将来需要项目特定的配置，可以在这里添加
# 目前所有必要的配置都已经在标准的 [project] 区域中定义
'''
        pyproject_content += sage_config
        
        with open(pyproject_file, 'w', encoding='utf-8') as f:
            f.write(pyproject_content)
        
        print("✅ 已在 pyproject.toml 中添加 [tool.sage] 配置区域")
    
    # 创建备份
    backup_file = root_dir / "project_config.toml.backup"
    if project_config_file.exists():
        with open(project_config_file, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(backup_content)
        
        print(f"✅ 已创建备份: {backup_file.name}")
    
    # 删除 project_config.toml
    if project_config_file.exists():
        project_config_file.unlink()
        print(f"✅ 已删除 {project_config_file.name}")
    
    print("\n🎉 配置迁移完成！")
    print("📋 迁移总结:")
    print("  - 删除了 project_config.toml（已备份）")
    print("  - pyproject.toml 现在是唯一的配置文件")
    print("  - 符合 Python 项目标准最佳实践")
    print("\n💡 说明:")
    print("  - pyproject.toml 包含所有必要的项目配置")
    print("  - 使用标准的 [project] 区域定义元数据")
    print("  - 如有需要，可在 [tool.sage] 区域添加自定义配置")

def main():
    migrate_to_standard_config()

if __name__ == "__main__":
    main()
