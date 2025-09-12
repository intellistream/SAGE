#!/usr/bin/env python3
"""
SAGE CLI 架构重构方案

目标：统一所有CLI脚本到 sage.tools.cli 目录下，建立清晰的层次结构

当前CLI分布：
1. packages/sage-tools/src/sage/tools/cli/ - 主CLI系统
2. packages/sage-tools/src/sage/tools/dev/cli.py - 开发工具CLI
3. packages/sage-tools/src/sage/tools/studio/cli.py - Studio CLI
4. packages/sage-tools/src/sage/tools/dev/cli/ - 开发CLI子命令

建议的统一架构：
packages/sage-tools/src/sage/tools/cli/
├── __init__.py              # CLI包初始化
├── main.py                  # 主CLI入口（原有）
├── core/                    # CLI核心框架（原有）
│   ├── __init__.py
│   ├── base.py
│   ├── config.py
│   └── utils.py
├── commands/                # 所有CLI命令（原有 + 新增）
│   ├── __init__.py
│   ├── cluster.py
│   ├── config.py
│   ├── deploy.py
│   ├── doctor.py
│   ├── extensions.py
│   ├── head.py
│   ├── job.py
│   ├── jobmanager.py
│   ├── studio.py           # 整合studio CLI
│   ├── version.py
│   ├── webui.py
│   ├── worker.py
│   └── dev/                # 开发相关命令子目录
│       ├── __init__.py
│       ├── analyze.py
│       ├── check_dependency.py
│       ├── clean.py
│       ├── home.py
│       ├── package.py
│       ├── publish.py
│       ├── pypi.py
│       ├── report.py
│       ├── status.py
│       ├── test.py
│       └── version.py
└── managers/               # 业务逻辑管理器（新增）
    ├── __init__.py
    ├── studio_manager.py   # 从 studio/cli.py 提取
    ├── dev_manager.py      # 从 dev/cli.py 提取
    └── webui_manager.py    # web UI 管理

重构步骤：
1. 移动 dev/cli.py 中的命令到 cli/commands/dev/
2. 移动 studio/cli.py 中的StudioManager到 cli/managers/
3. 更新所有导入引用
4. 更新主CLI的命令注册
5. 清理旧文件
"""

import os
import shutil
from pathlib import Path

class CLIRestructure:
    def __init__(self, sage_tools_path: str):
        self.tools_path = Path(sage_tools_path)
        self.cli_path = self.tools_path / "cli"
        
    def analyze_current_structure(self):
        """分析当前CLI结构"""
        print("🔍 当前CLI结构分析：")
        
        # 主CLI
        main_cli = self.cli_path
        if main_cli.exists():
            print(f"✅ 主CLI目录: {main_cli}")
            commands = list((main_cli / "commands").glob("*.py"))
            print(f"   - 命令数量: {len(commands)}")
            
        # Dev CLI
        dev_cli = self.tools_path / "dev" / "cli.py"
        if dev_cli.exists():
            print(f"✅ 开发CLI: {dev_cli}")
            
        dev_cli_dir = self.tools_path / "dev" / "cli"
        if dev_cli_dir.exists():
            dev_commands = list(dev_cli_dir.glob("**/*.py"))
            print(f"   - 开发命令数量: {len(dev_commands)}")
            
        # Studio CLI
        studio_cli = self.tools_path / "studio" / "cli.py"
        if studio_cli.exists():
            print(f"✅ Studio CLI: {studio_cli}")
            
    def create_unified_structure(self):
        """创建统一的CLI结构"""
        print("\n🚀 创建统一CLI结构...")
        
        # 创建managers目录
        managers_dir = self.cli_path / "managers"
        managers_dir.mkdir(exist_ok=True)
        
        # 创建dev子命令目录
        dev_commands_dir = self.cli_path / "commands" / "dev"
        dev_commands_dir.mkdir(exist_ok=True)
        
        print(f"✅ 创建目录: {managers_dir}")
        print(f"✅ 创建目录: {dev_commands_dir}")
        
    def move_studio_manager(self):
        """移动Studio管理器"""
        print("\n📦 移动Studio管理器...")
        
        source = self.tools_path / "studio" / "cli.py"
        target = self.cli_path / "managers" / "studio_manager.py"
        
        if source.exists():
            print(f"📝 从 {source} 提取StudioManager...")
            # 这里需要手动提取StudioManager类
            print(f"📁 目标位置: {target}")
            return True
        return False
        
    def move_dev_commands(self):
        """移动开发命令"""
        print("\n📦 移动开发命令...")
        
        dev_cli_dir = self.tools_path / "dev" / "cli"
        target_dir = self.cli_path / "commands" / "dev"
        
        if dev_cli_dir.exists():
            for py_file in dev_cli_dir.glob("**/*.py"):
                if py_file.name != "__init__.py":
                    rel_path = py_file.relative_to(dev_cli_dir)
                    target_file = target_dir / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    print(f"📁 移动: {py_file} -> {target_file}")
                    
    def update_imports(self):
        """更新导入引用"""
        print("\n🔄 更新导入引用...")
        print("   需要更新的模块：")
        print("   - cli/main.py - 添加dev子命令组")
        print("   - cli/commands/studio.py - 使用新的StudioManager")
        print("   - 所有迁移文件的内部导入")
        
    def run_restructure(self):
        """执行重构"""
        print("=" * 60)
        print("🔧 SAGE CLI 架构重构")
        print("=" * 60)
        
        self.analyze_current_structure()
        self.create_unified_structure()
        
        moved_studio = self.move_studio_manager()
        self.move_dev_commands()
        
        self.update_imports()
        
        print("\n" + "=" * 60)
        print("✨ 重构计划完成！")
        print("=" * 60)
        
        print("\n📋 下一步手动操作：")
        print("1. 提取StudioManager类到managers/studio_manager.py")
        print("2. 提取DevManager类到managers/dev_manager.py") 
        print("3. 更新cli/main.py添加dev子命令组")
        print("4. 更新所有导入路径")
        print("5. 清理旧文件")

if __name__ == "__main__":
    tools_path = "/home/shuhao/SAGE/packages/sage-tools/src/sage/tools"
    restructure = CLIRestructure(tools_path)
    restructure.run_restructure()
