#!/usr/bin/env python3
"""
SAGE 安全字节码发布工具
完全移除源代码，只保留字节码
"""

import os
import sys
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path

def remove_source_from_wheel(wheel_path: Path) -> bool:
    """从wheel中移除源代码，只保留字节码"""
    
    print(f"🔒 移除源代码: {wheel_path.name}")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 解压wheel
        extract_dir = temp_path / "extracted"
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            zf.extractall(extract_dir)
        
        # 找到所有.py文件并删除
        py_files = list(extract_dir.rglob("*.py"))
        removed_count = 0
        
        for py_file in py_files:
            # 检查是否有对应的.pyc文件
            rel_path = py_file.relative_to(extract_dir)
            parent_dir = py_file.parent
            
            # 查找__pycache__目录中的.pyc文件
            pycache_dir = parent_dir / "__pycache__"
            if pycache_dir.exists():
                pyc_files = list(pycache_dir.glob(f"{py_file.stem}.*.pyc"))
                opt_pyc_files = list(pycache_dir.glob(f"{py_file.stem}.*.opt-*.pyc"))
                
                # 如果有字节码文件，就删除源文件
                if pyc_files or opt_pyc_files:
                    py_file.unlink()
                    removed_count += 1
                    print(f"  🗑️ 删除: {rel_path}")
        
        print(f"  📊 移除了 {removed_count} 个源文件")
        
        # 重新打包wheel
        secure_wheel_path = wheel_path.parent / f"secure_{wheel_path.name}"
        
        with zipfile.ZipFile(secure_wheel_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in extract_dir.rglob("*"):
                if file_path.is_file():
                    arc_name = file_path.relative_to(extract_dir)
                    zf.write(file_path, arc_name)
        
        # 替换原wheel
        shutil.move(secure_wheel_path, wheel_path)
        
        return True

def create_secure_wheel(package_path: Path) -> bool:
    """创建安全的字节码wheel包"""
    
    print(f"🔧 处理包: {package_path.name}")
    
    # 保存当前目录
    original_cwd = os.getcwd()
    
    try:
        # 进入包目录
        os.chdir(package_path)
        
        # 清理旧构建
        for cleanup_dir in ["build", "dist"]:
            cleanup_path = Path(cleanup_dir)
            if cleanup_path.exists():
                shutil.rmtree(cleanup_path)
                print(f"  🧹 清理: {cleanup_dir}")
        
        # 设置Python字节码优化
        env = os.environ.copy()
        env['PYTHONOPTIMIZE'] = '2'  # 最高级别优化
        
        # 构建wheel，使用优化的字节码
        print("  📦 构建优化wheel...")
        
        result = subprocess.run([
            sys.executable, "-m", "build", "--wheel"
        ], env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 检查生成的文件
            wheel_files = list(Path("dist").glob("*.whl"))
            if wheel_files:
                wheel_file = wheel_files[0]
                print(f"  ✅ 构建成功: {wheel_file.name}")
                
                # 移除源代码
                if remove_source_from_wheel(wheel_file):
                    # 验证最终结果
                    verify_wheel_security(wheel_file)
                    return True
                else:
                    return False
            else:
                print("  ❌ 没有生成wheel文件")
                return False
        else:
            print(f"  ❌ 构建失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  💥 异常: {e}")
        return False
    
    finally:
        # 返回原目录
        os.chdir(original_cwd)

def verify_wheel_security(wheel_path: Path):
    """验证wheel的安全性"""
    
    with zipfile.ZipFile(wheel_path, 'r') as zf:
        files = zf.namelist()
        
        py_files = [f for f in files if f.endswith('.py') and not f.endswith('.pyc')]
        pyc_files = [f for f in files if f.endswith('.pyc') or f.endswith('.pyo')]
        
        print(f"  🔍 安全验证:")
        print(f"    📄 源文件: {len(py_files)}")
        print(f"    ⚡ 字节码文件: {len(pyc_files)}")
        
        if py_files:
            print(f"    ⚠️ 仍有源文件:")
            for py_file in py_files[:5]:  # 只显示前5个
                print(f"      - {py_file}")
        else:
            print(f"    ✅ 源代码已完全移除")

def create_setup_cfg(package_path: Path):
    """为包创建优化的setup.cfg"""
    
    setup_cfg_content = """[bdist_wheel]
universal = 0

[build_py]
compile = 1
optimize = 2

[install]
optimize = 2
compile = 1
"""
    
    setup_cfg = package_path / "setup.cfg"
    setup_cfg.write_text(setup_cfg_content)

def main():
    """主函数"""
    print("🔒 SAGE 安全字节码发布")
    print("=" * 40)
    print("📋 策略: 完全移除源代码，只保留字节码")
    print("🔒 效果: 源代码完全不可见")
    print()
    
    # 步骤1：配置字节码编译
    print("1️⃣ 配置所有包的字节码编译...")
    
    packages_to_build = [
        "packages/sage",
        "packages/sage-kernel", 
        "packages/sage-middleware",
        "packages/sage-apps"
    ]
    
    for package_dir in packages_to_build:
        package_path = Path(package_dir)
        if package_path.exists():
            create_setup_cfg(package_path)
            print(f"  📝 配置: {package_path.name}")
    
    print()
    
    # 步骤2：构建所有包
    print("2️⃣ 构建安全的wheel包...")
    
    successful_builds = []
    
    for package_dir in packages_to_build:
        package_path = Path(package_dir)
        if package_path.exists():
            if create_secure_wheel(package_path):
                successful_builds.append(package_path)
        else:
            print(f"⚠️ 包不存在: {package_dir}")
        print()
    
    # 步骤3：收集所有wheel到统一目录
    print("3️⃣ 收集wheel到dist目录...")
    
    project_dist = Path("dist")
    if not project_dist.exists():
        project_dist.mkdir()
    
    for package in successful_builds:
        wheel_files = list((package / "dist").glob("*.whl"))
        for wheel in wheel_files:
            target = project_dist / wheel.name
            shutil.copy2(wheel, target)
            print(f"  📦 收集: {wheel.name}")
    
    # 步骤4：总结
    print()
    print("4️⃣ 构建总结")
    print(f"✅ 成功构建: {len(successful_builds)} 个安全包")
    
    all_wheels = list(project_dist.glob("*.whl"))
    total_size = sum(w.stat().st_size for w in all_wheels) / 1024 / 1024  # MB
    
    print(f"📦 总计: {len(all_wheels)} 个wheel文件")
    print(f"💾 总大小: {total_size:.1f} MB")
    
    for wheel in all_wheels:
        file_size = wheel.stat().st_size / 1024  # KB
        print(f"  📦 {wheel.name} ({file_size:.1f} KB)")
    
    print()
    print("🎯 下一步: 使用以下命令发布到PyPI")
    print("twine upload dist/*.whl")

if __name__ == "__main__":
    main()
