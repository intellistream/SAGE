#!/usr/bin/env python3
"""
SAGE PyPI Installation Assistant
===============================

使用统一工具模块提供专业的PyPI安装体验。

Usage:
    sage-install
"""

import sys
from pathlib import Path

# 导入统一工具模块
try:
    from .unified_tools import logger, checker, interact, runner, create_progress_bar
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from unified_tools import logger, checker, interact, runner, create_progress_bar

def main():
    """主函数"""
    try:
        logger.print_header("🚀 SAGE PyPI Installation Assistant")
        print("Verifying your SAGE installation and helping you get started.")
        print("Run this after: pip install isage")
        print()
        
        # 系统要求检查
        logger.print_header("🔍 System Check")
        
        issues = []
        if not checker.check_python_version((3, 10)):
            issues.append("Python version")
        
        if not checker.check_command("pip", required=False):
            issues.append("pip availability")
            
        if issues:
            logger.print_error("System requirements not met. Please fix:")
            for issue in issues:
                print(f"  • {issue}")
            return False
        
        # SAGE安装检查
        logger.print_header("📦 SAGE Installation Check")
        progress = create_progress_bar(4)
        
        # 检查导入
        progress.update(1, "Checking SAGE import...")
        try:
            import sage
            logger.print_success("SAGE imported successfully")
        except ImportError:
            logger.print_error("SAGE not installed. Please run:")
            print("  pip install isage")
            logger.print_warning("If you just installed it, try restarting your terminal/Python session")
            return False
        
        # 检查版本
        progress.update(2, "Checking version...")
        try:
            version = getattr(sage, '__version__', 'Unknown')
            logger.print_success(f"SAGE version: {version}")
        except:
            logger.print_warning("Could not determine version")
        
        # 检查核心包
        progress.update(3, "Checking core packages...")
        missing_packages = []
        core_packages = ['sage.common', 'sage.kernel', 'sage.middleware', 'sage.apps']
        
        for pkg in core_packages:
            try:
                __import__(pkg)
                logger.print_debug(f"✓ {pkg} available")
            except ImportError:
                missing_packages.append(pkg)
        
        if missing_packages:
            logger.print_warning(f"Some packages missing: {', '.join(missing_packages)}")
            logger.print_warning("Consider running: pip install isage[full]")
        else:
            logger.print_success("All core packages available")
        
        # 检查CLI
        progress.update(4, "Checking CLI tools...")
        try:
            from sage.common.cli.main import app
            logger.print_success("CLI tools available")
            
            # 验证CLI命令可用性
            cli_success, cli_stdout, cli_stderr = runner.run_command([
                sys.executable, "-c", 
                "from sage.common.cli.main import app; print('CLI app loaded successfully')"
            ], "Verifying CLI functionality")
            
            if not cli_success:
                logger.print_warning("CLI app loaded but may have issues")
                logger.print_warning(f"CLI check stderr: {cli_stderr}")
                
        except ImportError as e:
            logger.print_error(f"CLI tools not available: {e}")
            logger.print_warning("CLI tools are required for full functionality")
            logger.print_warning("Try: pip install isage[cli] or pip install isage[full]")
            # 不返回False，因为这在最小安装中可能是正常的
        
        # JobManager检查和设置
        logger.print_header("🔗 JobManager Setup")
        
        try:
            # 检查JobManager状态的正确方法
            success, stdout, stderr = runner.run_command([
                sys.executable, "-c", 
                "from sage.common.cli.commands.jobmanager import JobManagerController; "
                "controller = JobManagerController(); "
                "health = controller.check_health(); "
                "print('running' if health.get('status') == 'success' else 'not_running')"
            ], "Checking JobManager status")
            
            if success and stdout and "running" in stdout.lower():
                logger.print_success("JobManager is running")
            else:
                logger.print_warning("JobManager not running")
                try:
                    if interact.confirm("Start JobManager now?", default=True):
                        # 使用sage命令启动JobManager
                        start_success, start_stdout, start_stderr = runner.run_command([
                            sys.executable, "-m", "sage.common.cli.main",
                            "jobmanager", "start", "--no-wait"
                        ], "Starting JobManager")
                        
                        if start_success:
                            logger.print_success("JobManager started!")
                        else:
                            logger.print_warning("Failed to start JobManager automatically")
                            print("Manual start: sage jobmanager start")
                except EOFError:
                    # 处理非交互环境（如conda run）
                    logger.print_warning("Non-interactive environment detected")
                    print("Manual start: sage jobmanager start")
        except Exception as e:
            logger.print_warning(f"JobManager check failed: {e}")
            print("Manual commands available:")
            print("  sage jobmanager status    # Check status") 
            print("  sage jobmanager start     # Start service")
        
        # 完成
        logger.print_header("🎉 SAGE Setup Complete!")
        print("Your SAGE installation has been verified and is ready to use.")
        print()
        print("🚀 Quick Start:")
        print("1. sage --help                    # View all available commands")
        print("2. sage doctor                    # Run system diagnostics") 
        print("3. sage jobmanager start          # Start the job manager service")
        print("4. sage job submit <script.py>    # Submit a job")
        print()
        print("📚 Learn More:")
        print("• Documentation: https://intellistream.github.io/SAGE-Pub/")
        print("• Examples: Check our GitHub repository examples/")
        print("• Community: https://github.com/intellistream/SAGE/discussions")
        print()
        print("🛠️ Installation Options:")
        print("• Full features: pip install isage[full]")
        print("• Development:   pip install isage[dev]")
        print("• Frontend only: pip install isage[frontend]")
        print()
        print("🆘 Need Help?")
        print("• Run: sage doctor")
        print("• Check: sage config show")
        print("• Report issues: https://github.com/intellistream/SAGE/issues")
        
        return True
        
    except KeyboardInterrupt:
        logger.print_warning("\n👋 Installation assistant cancelled.")
        return False
    except Exception as e:
        logger.print_error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
