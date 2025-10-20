#!/usr/bin/env python3
"""
SAGE Studio 可视化演示脚本

演示如何启动完整的可视化界面
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def print_banner():
    """打印启动横幅"""
    print("=" * 70)
    print("🎨 SAGE Studio 可视化界面演示")
    print("=" * 70)
    print()


def check_dependencies():
    """检查依赖项"""
    print("📋 检查依赖项...")
    
    studio_root = Path(__file__).parent
    frontend_dir = studio_root / "src" / "sage" / "studio" / "frontend"
    
    # 检查 Node.js
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        node_version = result.stdout.strip()
        print(f"  ✅ Node.js: {node_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ❌ Node.js 未安装")
        return False
    
    # 检查 npm
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        npm_version = result.stdout.strip()
        print(f"  ✅ npm: {npm_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ❌ npm 未安装")
        return False
    
    # 检查前端依赖
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists() and not node_modules.is_symlink():
        print("  ⚠️  前端依赖未安装")
        print("     运行: cd src/sage/studio/frontend && npm install")
        return False
    else:
        print(f"  ✅ 前端依赖已安装")
    
    # 检查 Python 依赖
    try:
        import fastapi
        import uvicorn
        print(f"  ✅ FastAPI 已安装")
    except ImportError:
        print("  ❌ FastAPI 未安装")
        print("     运行: pip install fastapi uvicorn")
        return False
    
    return True


def start_backend():
    """启动后端 API 服务"""
    print("\n🚀 启动后端 API 服务...")
    
    studio_root = Path(__file__).parent
    backend_file = studio_root / "src" / "sage" / "studio" / "config" / "backend" / "api.py"
    
    if not backend_file.exists():
        print(f"  ❌ 后端文件未找到: {backend_file}")
        return None
    
    try:
        # 启动后端进程
        process = subprocess.Popen(
            [sys.executable, str(backend_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        print(f"  ✅ 后端启动中... (PID: {process.pid})")
        print(f"  📡 API 地址: http://localhost:8080")
        
        # 等待后端启动
        print("  ⏳ 等待后端就绪...")
        time.sleep(3)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            print("  ✅ 后端启动成功")
            return process
        else:
            print("  ❌ 后端启动失败")
            return None
            
    except Exception as e:
        print(f"  ❌ 启动后端失败: {e}")
        return None


def start_frontend():
    """启动前端服务"""
    print("\n🎨 启动前端服务...")
    
    studio_root = Path(__file__).parent
    frontend_dir = studio_root / "src" / "sage" / "studio" / "frontend"
    
    if not frontend_dir.exists():
        print(f"  ❌ 前端目录未找到: {frontend_dir}")
        return None
    
    try:
        # 启动前端进程
        process = subprocess.Popen(
            ["npm", "start"],
            cwd=str(frontend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        print(f"  ✅ 前端启动中... (PID: {process.pid})")
        print(f"  🌐 前端地址: http://localhost:4200")
        
        # 等待前端编译和启动
        print("  ⏳ 等待 Angular 编译...")
        print("  💡 这可能需要 30-60 秒...")
        
        # 实时显示输出
        ready = False
        for line in process.stdout:
            print(f"     {line.rstrip()}")
            
            # 检查是否编译完成
            if "Compiled successfully" in line or "compiled successfully" in line:
                ready = True
                break
            
            # 检查是否有错误
            if "ERROR" in line or "error" in line.lower():
                print("  ❌ 前端编译出错")
                break
            
            # 超时保护（60秒）
            if time.time() - start_time > 60:
                print("  ⚠️  编译超时，但可能仍在继续...")
                break
        
        if ready or process.poll() is None:
            print("  ✅ 前端启动成功")
            return process
        else:
            print("  ❌ 前端启动失败")
            return None
            
    except Exception as e:
        print(f"  ❌ 启动前端失败: {e}")
        return None


def open_browser():
    """打开浏览器"""
    print("\n🌐 打开浏览器...")
    time.sleep(2)
    
    try:
        webbrowser.open("http://localhost:4200")
        print("  ✅ 浏览器已打开")
    except Exception as e:
        print(f"  ⚠️  自动打开浏览器失败: {e}")
        print("     请手动访问: http://localhost:4200")


def print_usage_info():
    """打印使用说明"""
    print("\n" + "=" * 70)
    print("📚 SAGE Studio 可视化界面使用指南")
    print("=" * 70)
    print()
    print("🎯 主要功能：")
    print("  1. 拓扑图编辑器 - 可视化设计工作流")
    print("  2. 作业监控面板 - 实时查看运行状态")
    print("  3. 操作符库浏览 - 查看可用节点")
    print("  4. 日志查看器 - 调试和监控")
    print()
    print("🔗 访问地址：")
    print("  前端: http://localhost:4200")
    print("  后端: http://localhost:8080")
    print("  API 文档: http://localhost:8080/docs")
    print()
    print("⚙️  停止服务：")
    print("  按 Ctrl+C 停止所有服务")
    print()
    print("=" * 70)


def main():
    """主函数"""
    start_time = time.time()
    
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，无法启动")
        sys.exit(1)
    
    backend_process = None
    frontend_process = None
    
    try:
        # 启动后端
        backend_process = start_backend()
        if not backend_process:
            print("\n❌ 后端启动失败")
            sys.exit(1)
        
        # 启动前端
        start_time = time.time()
        frontend_process = start_frontend()
        if not frontend_process:
            print("\n❌ 前端启动失败")
            if backend_process:
                backend_process.terminate()
            sys.exit(1)
        
        # 打开浏览器
        open_browser()
        
        # 打印使用说明
        print_usage_info()
        
        # 保持运行
        print("✨ SAGE Studio 可视化界面运行中...")
        print("   按 Ctrl+C 停止服务\n")
        
        # 监控进程
        while True:
            time.sleep(1)
            
            # 检查后端是否还在运行
            if backend_process.poll() is not None:
                print("❌ 后端进程已退出")
                break
            
            # 检查前端是否还在运行
            if frontend_process.poll() is not None:
                print("❌ 前端进程已退出")
                break
    
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号...")
    
    finally:
        # 清理进程
        print("🧹 清理进程...")
        
        if frontend_process and frontend_process.poll() is None:
            print("  停止前端服务...")
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
            print("  ✅ 前端已停止")
        
        if backend_process and backend_process.poll() is None:
            print("  停止后端服务...")
            backend_process.terminate()
            backend_process.wait(timeout=5)
            print("  ✅ 后端已停止")
        
        print("\n👋 SAGE Studio 已停止")


if __name__ == "__main__":
    main()
