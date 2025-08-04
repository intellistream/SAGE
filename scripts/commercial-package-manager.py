#!/usr/bin/env python3
"""
SAGE商业包管理器

用于管理和部署商业版SAGE包的工具。
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import json

class CommercialPackageManager:
    """商业包管理器"""
    
    def __init__(self):
        self.root_path = Path(__file__).parent.parent
        self.commercial_path = self.root_path / "packages" / "commercial"
        self.packages = {
            "sage-kernel": {
                "path": self.commercial_path / "sage-kernel",
                "description": "High-performance kernel infrastructure",
                "components": ["sage_queue"]
            },
            "sage-middleware": {
                "path": self.commercial_path / "sage-middleware", 
                "description": "Database and storage middleware",
                "components": ["sage_db"]
            },
            "sage-userspace": {
                "path": self.commercial_path / "sage-userspace",
                "description": "High-level application components",
                "components": []
            }
        }
    
    def list_packages(self):
        """列出所有商业包"""
        print("SAGE Commercial Packages:")
        print("=" * 50)
        for name, info in self.packages.items():
            print(f"\n📦 {name}")
            print(f"   Description: {info['description']}")
            print(f"   Path: {info['path']}")
            print(f"   Components: {', '.join(info['components']) if info['components'] else 'None'}")
            print(f"   Status: {'✅ Available' if info['path'].exists() else '❌ Missing'}")
    
    def build_package(self, package_name: str):
        """构建指定的商业包"""
        if package_name not in self.packages:
            print(f"❌ Unknown package: {package_name}")
            return False
            
        package_info = self.packages[package_name]
        package_path = package_info["path"]
        
        if not package_path.exists():
            print(f"❌ Package path does not exist: {package_path}")
            return False
            
        print(f"🔨 Building {package_name}...")
        
        try:
            # 切换到包目录
            os.chdir(package_path)
            
            # 使用pip安装editable模式
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-e", "."
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Successfully built {package_name}")
                return True
            else:
                print(f"❌ Failed to build {package_name}")
                print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False
        finally:
            # 回到原目录
            os.chdir(self.root_path)
    
    def build_all(self):
        """构建所有商业包"""
        print("🔨 Building all commercial packages...")
        success_count = 0
        
        for package_name in self.packages.keys():
            if self.build_package(package_name):
                success_count += 1
                
        print(f"\n📊 Build Summary: {success_count}/{len(self.packages)} packages built successfully")
        return success_count == len(self.packages)
    
    def validate_structure(self):
        """验证商业包目录结构"""
        print("🔍 Validating commercial package structure...")
        
        all_valid = True
        for name, info in self.packages.items():
            print(f"\n📦 Checking {name}...")
            package_path = info["path"]
            
            # 检查基本文件
            required_files = [
                "pyproject.toml",
                "README.md", 
                "src/sage/__init__.py"
            ]
            
            for file_path in required_files:
                full_path = package_path / file_path
                if full_path.exists():
                    print(f"   ✅ {file_path}")
                else:
                    print(f"   ❌ {file_path} (missing)")
                    all_valid = False
        
        if all_valid:
            print("\n✅ All commercial packages have valid structure")
        else:
            print("\n❌ Some packages have structural issues")
            
        return all_valid
    
    def generate_manifest(self):
        """生成商业包清单"""
        manifest = {
            "sage_commercial_packages": {
                "version": "1.0.0",
                "generated_at": str(Path.cwd()),
                "packages": {}
            }
        }
        
        for name, info in self.packages.items():
            manifest["sage_commercial_packages"]["packages"][name] = {
                "path": str(info["path"].relative_to(self.root_path)),
                "description": info["description"],
                "components": info["components"],
                "exists": info["path"].exists()
            }
        
        manifest_path = self.commercial_path / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        print(f"📋 Commercial package manifest generated: {manifest_path}")
        return manifest_path


def main():
    """主函数"""
    manager = CommercialPackageManager()
    
    if len(sys.argv) < 2:
        print("Usage: python commercial-package-manager.py <command>")
        print("\nCommands:")
        print("  list      - List all commercial packages")
        print("  build     - Build specific package (usage: build <package-name>)")
        print("  build-all - Build all commercial packages")
        print("  validate  - Validate package structure")
        print("  manifest  - Generate package manifest")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        manager.list_packages()
    elif command == "build":
        if len(sys.argv) < 3:
            print("Usage: build <package-name>")
            manager.list_packages()
        else:
            manager.build_package(sys.argv[2])
    elif command == "build-all":
        manager.build_all()
    elif command == "validate":
        manager.validate_structure()
    elif command == "manifest":
        manager.generate_manifest()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
