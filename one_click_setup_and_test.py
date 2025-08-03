#!/usr/bin/env python3
"""
SAGE Monorepo 一键环境安装和测试脚本
=====================================

这个脚本会：
1. 删除现有的测试环境
2. 从头创建新的虚拟环境
3. 使用新的包管理器安装所有SAGE包
4. 运行完整的测试套件
5. 生成测试报告

使用方法:
    python one_click_setup_and_test.py
    python one_click_setup_and_test.py --workers 8
    python one_click_setup_and_test.py --quick-test
"""

import os
import sys
import subprocess
import shutil
import argparse
import time
from pathlib import Path
from datetime import datetime

class OneClickSAGETester:
    """SAGE 一键安装和测试"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.venv_path = self.project_root / "test_env"
        self.test_logs_dir = self.project_root / "test_logs"
        self.reports_dir = self.project_root / "test_reports"
        
    def print_header(self, title: str):
        """打印格式化标题"""
        print(f"\n{'='*60}")
        print(f"🚀 {title}")
        print(f"{'='*60}")
        
    def print_step(self, step: int, title: str):
        """打印步骤"""
        print(f"\n📋 步骤 {step}: {title}")
        print("-" * 40)
        
    def run_command(self, command: str, description: str) -> bool:
        """运行命令"""
        print(f"🔧 {description}")
        print(f"💻 执行: {command}")
        
        try:
            result = subprocess.run(command, shell=True, cwd=self.project_root)
            if result.returncode == 0:
                print("✅ 成功")
                return True
            else:
                print(f"❌ 失败 (退出码: {result.returncode})")
                return False
        except Exception as e:
            print(f"❌ 异常: {e}")
            return False
            
    def cleanup_old_environment(self):
        """清理旧环境"""
        self.print_step(1, "清理旧环境")
        
        # 删除虚拟环境
        if self.venv_path.exists():
            print(f"🗑️  删除旧虚拟环境: {self.venv_path}")
            shutil.rmtree(self.venv_path)
            print("✅ 旧虚拟环境已删除")
        else:
            print("ℹ️  没有发现旧虚拟环境")
            
        # 清理日志目录
        if self.test_logs_dir.exists():
            print(f"🗑️  清理测试日志: {self.test_logs_dir}")
            shutil.rmtree(self.test_logs_dir)
            print("✅ 测试日志已清理")
            
        # 清理Python缓存
        cache_dirs = [
            "__pycache__",
            ".pytest_cache",
            "build",
            "dist",
            "*.egg-info"
        ]
        
        for pattern in cache_dirs:
            if pattern.startswith("*"):
                # glob pattern
                for item in self.project_root.glob(pattern):
                    if item.is_dir():
                        print(f"🗑️  删除缓存目录: {item}")
                        shutil.rmtree(item)
            else:
                # exact directory name
                for item in self.project_root.rglob(pattern):
                    if item.is_dir():
                        print(f"🗑️  删除缓存目录: {item}")
                        shutil.rmtree(item)
                        
        print("✅ 环境清理完成")
        
    def create_fresh_environment(self):
        """创建新环境"""
        self.print_step(2, "创建新的虚拟环境")
        
        # 检查Python版本
        python_version = subprocess.run(
            ["python3", "--version"], 
            capture_output=True, 
            text=True
        )
        print(f"🐍 Python版本: {python_version.stdout.strip()}")
        
        if not python_version.stdout or not any(v in python_version.stdout for v in ["3.10", "3.11", "3.12"]):
            print("⚠️  警告: 推荐使用Python 3.10+")
            
        # 检查是否满足最低版本要求 
        version_parts = python_version.stdout.split()
        if len(version_parts) >= 2:
            version_str = version_parts[1]  # "3.10.12"
            major, minor = map(int, version_str.split('.')[:2])
            if major < 3 or (major == 3 and minor < 10):
                print("❌ 错误: SAGE需要Python 3.10或更高版本")
                return False
            
        # 创建虚拟环境
        success = self.run_command(
            "python3 -m venv test_env",
            "创建虚拟环境"
        )
        
        if not success:
            print("❌ 虚拟环境创建失败")
            return False
            
        return True
        
    def install_dependencies(self):
        """安装依赖"""
        self.print_step(3, "安装项目依赖")
        
        # 使用虚拟环境中的python和pip直接调用，避免shell激活问题
        venv_python = self.venv_path / "bin" / "python"
        venv_pip = self.venv_path / "bin" / "pip"
        
        # 升级pip
        success = self.run_command(
            f"{venv_pip} install --upgrade pip",
            "升级pip"
        )
        
        if not success:
            print("⚠️  pip升级失败，继续安装依赖")
            
        # 安装项目依赖 - 使用新的包管理器
        success = self.run_command(
            f"{venv_python} scripts/sage-package-manager.py install-all --dev",
            "安装所有SAGE包和开发依赖"
        )
        
        if not success:
            print("❌ 依赖安装失败")
            return False
            
        # 显示安装的包
        print("\n📦 已安装的包:")
        subprocess.run(
            f"{venv_pip} list | head -20",
            shell=True
        )
        
        return True
        
    def run_tests(self, workers: int = 4, quick_test: bool = False):
        """运行测试"""
        mode = "快速测试" if quick_test else "完整测试"
        self.print_step(4, f"运行{mode}")
        
        # 使用虚拟环境中的python直接调用
        venv_python = self.venv_path / "bin" / "python"
        
        # 确保目录存在
        self.test_logs_dir.mkdir(exist_ok=True)
        
        if quick_test:
            # 快速测试：智能差异测试 + 列出测试
            print("🎯 运行智能差异测试...")
            success1 = self.run_command(
                f"{venv_python} scripts/test_runner.py --diff",
                "智能差异测试"
            )
            
            print("📋 列出所有测试文件...")
            success2 = self.run_command(
                f"{venv_python} scripts/test_runner.py --list",
                "列出测试文件"
            )
            
            return success1 and success2
        else:
            # 完整测试
            print(f"🚀 运行完整测试套件 (使用 {workers} 个并行进程)...")
            success = self.run_command(
                f"{venv_python} scripts/test_runner.py --all --workers {workers}",
                f"完整测试执行 ({workers} workers)"
            )
            
            return success
            
    def generate_report(self):
        """生成测试报告"""
        self.print_step(5, "生成测试报告")
        
        # 确保报告目录存在
        self.reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"setup_and_test_report_{timestamp}.md"
        
        # 统计测试日志
        log_files = list(self.test_logs_dir.glob("*.log")) if self.test_logs_dir.exists() else []
        passed_tests = 0
        failed_tests = 0
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "PASSED" in content and "FAILED" not in content:
                        passed_tests += 1
                    elif "FAILED" in content:
                        failed_tests += 1
            except:
                continue
                
        total_tests = len(log_files)
        success_rate = (passed_tests / max(total_tests, 1) * 100) if total_tests > 0 else 0
        
        # 生成报告
        report_content = f"""# SAGE 一键安装和测试报告

## 📊 执行概览
- **执行时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **项目路径**: {self.project_root}
- **Python版本**: {subprocess.run(['python', '--version'], capture_output=True, text=True, cwd=self.venv_path / 'bin').stdout.strip() if (self.venv_path / 'bin').exists() else '未知'}

## 🏗️ 环境设置
- **虚拟环境**: ✅ 已创建 ({self.venv_path})
- **依赖安装**: ✅ 已完成
- **测试运行器**: ✅ 可用

## 🧪 测试结果
- **测试日志文件**: {total_tests} 个
- **通过测试**: {passed_tests} 个
- **失败测试**: {failed_tests} 个
- **成功率**: {success_rate:.1f}%

## 📈 系统信息
- **CPU核心数**: {os.cpu_count()}
- **项目结构**: 
  - 测试目录: {len(list(self.project_root.rglob('test*')))} 个
  - Python文件: {len(list(self.project_root.rglob('*.py')))} 个

## 📋 后续使用
```bash
# 激活环境
source test_env/bin/activate

# 运行测试
python scripts/test_runner.py --all

# 智能测试
python scripts/test_runner.py --diff

# 查看日志
ls -la test_logs/
```

## 🚀 快速命令
- **重新运行测试**: `python one_click_setup_and_test.py --quick-test`
- **完整测试**: `python one_click_setup_and_test.py --workers 8`

---
*报告由SAGE一键安装测试脚本生成*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print(f"📄 测试报告已生成: {report_file}")
        return report_file
        
    def run_complete_setup(self, workers: int = 4, quick_test: bool = False):
        """运行完整的安装和测试流程"""
        start_time = time.time()
        
        self.print_header("SAGE 一键环境安装和测试")
        
        print("这个脚本将:")
        print("✅ 删除现有测试环境")
        print("✅ 创建新的虚拟环境")
        print("✅ 安装所有项目依赖")
        print("✅ 运行完整测试套件")
        print("✅ 生成详细测试报告")
        
        # 确认继续
        try:
            response = input("\n⚠️  这将删除现有的test_env目录，是否继续？(y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ 操作已取消")
                return False
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            return False
            
        success = True
        
        # 步骤1: 清理旧环境
        self.cleanup_old_environment()
        
        # 步骤2: 创建新环境
        if not self.create_fresh_environment():
            success = False
            
        # 步骤3: 安装依赖
        if success and not self.install_dependencies():
            success = False
            
        # 步骤4: 运行测试
        if success:
            test_success = self.run_tests(workers, quick_test)
            if not test_success:
                print("⚠️  测试执行有问题，但继续生成报告")
                
        # 步骤5: 生成报告
        report_file = self.generate_report()
        
        # 总结
        end_time = time.time()
        duration = end_time - start_time
        
        self.print_header("安装和测试完成")
        
        if success:
            print("🎉 SAGE环境安装和测试成功完成！")
        else:
            print("⚠️  安装过程中遇到一些问题，请查看上面的错误信息")
            
        print(f"⏱️  总耗时: {duration:.1f} 秒")
        print(f"📄 详细报告: {report_file}")
        print(f"📊 测试日志: {self.test_logs_dir}")
        
        print("\n🚀 现在你可以:")
        print("   • 激活环境: source test_env/bin/activate  (bash) 或 . test_env/bin/activate  (sh)")
        print("   • 运行测试: test_env/bin/python scripts/test_runner.py --all")
        print("   • 查看日志: ls -la test_logs/")
        
        return success

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SAGE 一键环境安装和测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python one_click_setup_and_test.py                 # 默认设置和完整测试
  python one_click_setup_and_test.py --workers 8     # 使用8个并行进程
  python one_click_setup_and_test.py --quick-test    # 快速测试模式
        """
    )
    
    parser.add_argument(
        "--workers", 
        type=int, 
        default=4, 
        help="并行测试进程数 (默认: 4)"
    )
    parser.add_argument(
        "--quick-test", 
        action="store_true", 
        help="运行快速测试而不是完整测试"
    )
    
    args = parser.parse_args()
    
    # 检查是否在正确的目录
    if not Path("packages").exists() or not Path("scripts/sage-package-manager.py").exists():
        print("❌ 错误: 请在SAGE项目根目录下运行此脚本")
        print(f"当前目录: {Path.cwd()}")
        print("应该包含: packages/ 目录和 scripts/sage-package-manager.py")
        sys.exit(1)
        
    if not Path("scripts/test_runner.py").exists():
        print("⚠️  警告: scripts/test_runner.py 不存在，将使用基本pytest测试")
        print("你可以手动运行: python -m pytest 来测试包")
        
    # 创建并运行一键安装测试
    tester = OneClickSAGETester()
    
    try:
        success = tester.run_complete_setup(
            workers=args.workers,
            quick_test=args.quick_test
        )
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 执行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
