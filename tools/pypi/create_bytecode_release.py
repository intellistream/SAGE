#!/usr/bin/env python3
"""
SAGE 字节码发布工具 - 最终版本
通过字节码编译隐藏企业版源代码
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

def create_bytecode_wheel(package_path: Path) -> bool:
    """为指定包创建字节码wheel"""
    
    print(f"🔧 处理包: {package_path.name}")
    
    # 进入包目录
    original_cwd = os.getcwd()
    os.chdir(package_path)
    
    try:
        # 清理旧构建
        for cleanup_dir in ["build", "dist", "*.egg-info"]:
            for path in Path(".").glob(cleanup_dir):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        
        # 步骤1：正常构建wheel
        print("  📦 构建标准wheel...")
        result = subprocess.run([
            sys.executable, "-m", "build", "--wheel"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"  ❌ 构建失败: {result.stderr}")
            return False
        
        # 步骤2：修改wheel内容为字节码
        wheel_files = list(Path("dist").glob("*.whl"))
        if not wheel_files:
            print("  ❌ 没有找到wheel文件")
            return False
        
        wheel_file = wheel_files[0]
        print(f"  🔄 转换wheel为字节码版本: {wheel_file.name}")
        
        # 使用临时目录处理wheel
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            extract_dir = temp_path / "wheel_content"
            
            # 解压wheel
            shutil.unpack_archive(wheel_file, extract_dir, 'zip')
            
            # 编译Python文件为字节码
            python_files = list(extract_dir.rglob("*.py"))
            compiled_count = 0
            
            for py_file in python_files:
                # 跳过一些不需要编译的文件
                if any(skip in str(py_file) for skip in ['.egg-info', '__pycache__']):
                    continue
                
                try:
                    # 使用py_compile编译
                    import py_compile
                    
                    # 编译为.pyc，但重命名为.py (这样setuptools会正确处理)
                    pyc_content = py_compile.compile(py_file, doraise=True, optimize=2)
                    
                    # 读取编译后的字节码
                    import marshal
                    import importlib.util
                    
                    # 简单方法：编译到内存然后写入
                    with open(py_file, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    # 编译源代码
                    compiled_code = compile(source, str(py_file), 'exec', optimize=2)
                    
                    # 创建.pyc内容 (简化版本，只包含字节码)
                    # 实际生产环境中可能需要更复杂的处理
                    pyc_data = marshal.dumps(compiled_code)
                    
                    # 替换原文件内容为字节码标记
                    obfuscated_content = f'''# This file contains compiled bytecode
# Original source code is not available
# 此文件包含编译的字节码，原始源代码不可见

import marshal
import types

# Compiled bytecode (base64 encoded to avoid issues)
import base64
_code_data = base64.b64decode({base64.b64encode(pyc_data).decode()!r})
_code = marshal.loads(_code_data)

# Execute the compiled code in current namespace
exec(_code, globals())
'''
                    
                    # 写入混淆后的文件
                    py_file.write_text(obfuscated_content, encoding='utf-8')
                    compiled_count += 1
                    
                except Exception as e:
                    print(f"    ⚠️ 编译失败 {py_file.name}: {e}")
                    # 保持原文件不变
            
            print(f"  ✅ 编译了 {compiled_count} 个文件")
            
            # 重新打包wheel
            new_wheel_name = wheel_file.stem + "_bytecode.whl"
            new_wheel_path = Path("dist") / new_wheel_name
            
            # 删除旧wheel
            wheel_file.unlink()
            
            # 创建新wheel
            shutil.make_archive(
                str(new_wheel_path.with_suffix('')), 
                'zip', 
                extract_dir
            )
            
            # 重命名为.whl
            zip_file = new_wheel_path.with_suffix('.zip')
            if zip_file.exists():
                zip_file.rename(new_wheel_path)
            
            print(f"  🎉 字节码wheel创建完成: {new_wheel_path.name}")
            return True
            
    except Exception as e:
        print(f"  💥 处理异常: {e}")
        return False
    
    finally:
        os.chdir(original_cwd)

def main():
    """主函数"""
    print("🎯 SAGE 字节码发布工具")
    print("=" * 50)
    print("⚠️  注意：这将创建字节码版本的wheel文件")
    print("⚠️  用户将无法看到原始Python源代码")
    print()
    
    # 检查环境
    packages_to_process = [
        "packages/sage",
        "packages/sage-kernel", 
        "packages/sage-middleware",
        "packages/sage-apps"
    ]
    
    success_count = 0
    
    for package_dir in packages_to_process:
        package_path = Path(package_dir)
        
        if not package_path.exists():
            print(f"⚠️ 跳过不存在的包: {package_dir}")
            continue
        
        if create_bytecode_wheel(package_path):
            success_count += 1
            print()
    
    print(f"🎉 完成！成功处理 {success_count} 个包")
    print()
    print("📋 后续步骤:")
    print("1. 检查生成的wheel文件内容")
    print("2. 测试wheel安装和功能")
    print("3. 上传到PyPI: twine upload dist/*_bytecode.whl")

if __name__ == "__main__":
    # 需要base64模块
    import base64
    main()
