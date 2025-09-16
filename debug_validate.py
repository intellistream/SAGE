#!/usr/bin/env python3
"""
调试PyPI验证脚本
"""
import subprocess
import sys
import tempfile
import os
from pathlib import Path

def debug_validate():
    print("🔍 调试PyPI验证问题")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        venv_path = temp_path / "debug_venv"
        
        print(f"📁 临时目录: {temp_path}")
        
        # 创建虚拟环境
        print("🔧 创建虚拟环境...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        
        # 设置路径
        if sys.platform == "win32":
            python_exe = venv_path / "Scripts" / "python.exe"
            pip_exe = venv_path / "Scripts" / "pip.exe"
        else:
            python_exe = venv_path / "bin" / "python"
            pip_exe = venv_path / "bin" / "pip"
        
        # 升级pip
        print("📦 升级pip...")
        subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip", "--quiet"], check=True)
        
        # 找到wheel文件
        wheel_path = Path("/home/shuhao/SAGE/packages/sage/dist/isage-0.1.3.1-py3-none-any.whl")
        if not wheel_path.exists():
            print(f"❌ Wheel文件不存在: {wheel_path}")
            return
            
        print(f"📦 找到wheel文件: {wheel_path}")
        
        # 尝试使用--no-deps安装（模拟验证脚本）
        print("🔨 使用--no-deps安装（模拟验证脚本）...")
        result = subprocess.run([str(pip_exe), "install", str(wheel_path), "--quiet", "--no-deps"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 安装失败: {result.stderr}")
            return
        print("✅ 安装成功")
        
        # 尝试导入并获取版本（模拟验证脚本）
        print("🔍 测试导入...")
        result = subprocess.run([str(python_exe), "-c", "import sage; print(f'sage.__version__ = {sage.__version__}')"], 
                              capture_output=True, text=True)
        print(f"返回码: {result.returncode}")
        print(f"输出: {result.stdout}")
        print(f"错误: {result.stderr}")
        
        if result.returncode != 0:
            print("\n🔍 详细调试...")
            # 检查安装的包结构
            result2 = subprocess.run([str(python_exe), "-c", 
                "import sage; print(f'sage.__file__ = {sage.__file__}'); print(f'sage.__path__ = {sage.__path__}'); import os; print('文件列表:'); [print(f'  {f}') for f in os.listdir(os.path.dirname(sage.__file__))]"], 
                capture_output=True, text=True)
            print("包结构调试:")
            print(result2.stdout)
            if result2.stderr:
                print("错误:", result2.stderr)
                
            # 检查是否有_version.py
            result3 = subprocess.run([str(python_exe), "-c", 
                "import sage; import os; version_file = os.path.join(os.path.dirname(sage.__file__), '_version.py'); print(f'_version.py exists: {os.path.exists(version_file)}'); print(f'_version.py path: {version_file}')"], 
                capture_output=True, text=True)
            print("版本文件检查:")
            print(result3.stdout)
            
        print("\n" + "="*50)
        
        # 现在尝试正常安装（包含依赖）
        print("🔨 正常安装（包含依赖）...")
        subprocess.run([str(pip_exe), "uninstall", "isage", "-y", "--quiet"], check=True)
        result = subprocess.run([str(pip_exe), "install", str(wheel_path), "--quiet"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 安装失败: {result.stderr}")
            return
        print("✅ 安装成功")
        
        # 再次测试导入
        print("🔍 测试导入...")
        result = subprocess.run([str(python_exe), "-c", "import sage; print(f'sage.__version__ = {sage.__version__}')"], 
                              capture_output=True, text=True)
        print(f"返回码: {result.returncode}")
        print(f"输出: {result.stdout}")
        print(f"错误: {result.stderr}")

if __name__ == "__main__":
    debug_validate()