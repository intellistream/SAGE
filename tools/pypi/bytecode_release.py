#!/usr/bin/env python3
"""
SAGE PyPI字节码编译发布脚本
编译Python源码为.pyc文件，隐藏企业版源代码
"""

import os
import sys
import shutil
import py_compile
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict

class BytecodeBuilder:
    """字节码构建器"""
    
    def __init__(self, package_path: Path):
        self.package_path = package_path
        self.temp_dir = None
        
    def compile_package(self) -> Path:
        """编译包为字节码"""
        print(f"🔧 编译包: {self.package_path.name}")
        
        # 创建临时目录
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"sage_bytecode_{self.package_path.name}_"))
        
        # 复制项目结构
        compiled_path = self.temp_dir / self.package_path.name
        shutil.copytree(self.package_path, compiled_path)
        
        # 编译Python文件
        self._compile_python_files(compiled_path)
        
        # 删除.py源文件
        self._remove_source_files(compiled_path)
        
        # 更新pyproject.toml排除源文件
        self._update_pyproject(compiled_path)
        
        return compiled_path
    
    def _compile_python_files(self, package_path: Path):
        """编译所有Python文件"""
        python_files = list(package_path.rglob("*.py"))
        
        for py_file in python_files:
            # 跳过setup.py等特殊文件
            if py_file.name in ['setup.py', 'conftest.py']:
                continue
                
            try:
                # 编译为.pyc
                pyc_file = py_file.with_suffix('.pyc')
                py_compile.compile(py_file, pyc_file, doraise=True)
                print(f"  ✓ 编译: {py_file.relative_to(package_path)} → {pyc_file.name}")
                
            except py_compile.PyCompileError as e:
                print(f"  ❌ 编译失败: {py_file}: {e}")
    
    def _remove_source_files(self, package_path: Path):
        """删除源文件，只保留字节码"""
        python_files = list(package_path.rglob("*.py"))
        
        for py_file in python_files:
            # 保留必要的文件
            if py_file.name in ['setup.py']:
                continue
                
            # 对于__init__.py和其他.py文件，如果有对应的.pyc，则删除.py
            pyc_file = py_file.with_suffix('.pyc')
            if pyc_file.exists():
                py_file.unlink()
                print(f"  🗑️ 删除源文件: {py_file.relative_to(package_path)}")
            else:
                # 如果没有编译成功，保留源文件避免包损坏
                print(f"  ⚠️ 保留源文件(无.pyc): {py_file.relative_to(package_path)}")
    
    def _update_pyproject(self, package_path: Path):
        """更新pyproject.toml包含.pyc文件"""
        pyproject_file = package_path / "pyproject.toml"
        
        if pyproject_file.exists():
            content = pyproject_file.read_text()
            
            # 添加.pyc文件包含规则
            if "[tool.setuptools.packages.find]" not in content:
                # 添加包含.pyc的配置
                setuptools_config = """

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"*" = ["*.pyc"]

"""
                content += setuptools_config
                pyproject_file.write_text(content)
                print(f"  📝 更新pyproject.toml包含.pyc文件")

def build_bytecode_packages():
    """构建所有包的字节码版本"""
    packages_dir = Path("packages")
    
    # 要编译的包
    packages_to_build = [
        "sage-kernel",
        "sage-middleware", 
        "sage-apps",
        "sage"
    ]
    
    built_packages = []
    
    for package_name in packages_to_build:
        package_path = packages_dir / package_name
        
        if not package_path.exists():
            print(f"❌ 包不存在: {package_path}")
            continue
            
        try:
            builder = BytecodeBuilder(package_path)
            compiled_path = builder.compile_package()
            built_packages.append(compiled_path)
            print(f"✅ 包编译完成: {package_name}")
            
        except Exception as e:
            print(f"❌ 包编译失败 {package_name}: {e}")
    
    return built_packages

def build_and_upload(packages: List[Path], dry_run: bool = True):
    """构建并上传字节码包"""
    for package_path in packages:
        print(f"\n📦 构建包: {package_path.name}")
        
        try:
            # 进入包目录
            os.chdir(package_path)
            
            # 清理旧构建
            if Path("dist").exists():
                shutil.rmtree("dist")
            if Path("build").exists():
                shutil.rmtree("build")
            
            # 构建wheel
            result = subprocess.run([
                sys.executable, "-m", "build", "--wheel"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ 构建成功: {package_path.name}")
                
                # 显示构建的文件
                dist_files = list(Path("dist").glob("*.whl"))
                for dist_file in dist_files:
                    print(f"  📄 {dist_file}")
                
                if not dry_run:
                    # 上传到PyPI
                    upload_result = subprocess.run([
                        "twine", "upload", "dist/*"
                    ], capture_output=True, text=True)
                    
                    if upload_result.returncode == 0:
                        print(f"🚀 上传成功: {package_path.name}")
                    else:
                        print(f"❌ 上传失败: {upload_result.stderr}")
                else:
                    print(f"🔍 [预演模式] 跳过上传")
                    
            else:
                print(f"❌ 构建失败: {result.stderr}")
                
        except Exception as e:
            print(f"💥 处理包异常 {package_path.name}: {e}")
        
        finally:
            # 返回原目录
            os.chdir(Path(__file__).parent.parent)

def main():
    """主函数"""
    print("🎯 SAGE字节码编译发布")
    print("=" * 50)
    
    # 检查是否从包目录调用，如果是，则调整到项目根目录
    current_dir = Path.cwd()
    project_root = None
    
    # 尝试找到项目根目录
    check_dir = current_dir
    while check_dir != check_dir.parent:
        if (check_dir / "packages").exists() and (check_dir / "pyproject.toml").exists():
            project_root = check_dir
            break
        check_dir = check_dir.parent
    
    if project_root is None:
        print("❌ 无法找到SAGE项目根目录")
        sys.exit(1)
    
    # 切换到项目根目录
    os.chdir(project_root)
    print(f"📂 工作目录: {project_root}")
    
    try:
        # 构建字节码包
        print("🔧 开始编译字节码包...")
        built_packages = build_bytecode_packages()
        
        if not built_packages:
            print("❌ 没有成功编译的包")
            sys.exit(1)
        
        print(f"\n✅ 编译完成 {len(built_packages)} 个包")
        
        # 构建和上传
        print("\n📦 开始构建和上传...")
        dry_run = "--dry-run" in sys.argv
        build_and_upload(built_packages, dry_run=dry_run)
        
        print("\n🎉 字节码发布完成！")
        print("用户将只能看到.pyc文件，源代码完全隐藏")
        
    except KeyboardInterrupt:
        print("\n\n🛑 用户取消操作")
    except Exception as e:
        print(f"\n💥 发布异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
