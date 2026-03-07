"""
Git Hooks Installer for SAGE Development.

Handles installation, uninstallation, and management of Git hooks
for code quality and architecture compliance checks.
"""

import subprocess
import sys
from pathlib import Path


class HooksInstaller:
    """Installer for SAGE Git hooks."""

    LIGHTWEIGHT = "lightweight"
    FULL = "full"
    _VALID_MODES = {LIGHTWEIGHT, FULL}

    def __init__(
        self,
        root_dir: Path | None = None,
        quiet: bool = False,
        mode: str = LIGHTWEIGHT,
    ):
        """
        Initialize the hooks installer.

        Args:
            root_dir: Root directory of the SAGE project. If None, auto-detect from git.
            quiet: If True, suppress non-error output.
        """
        self.quiet = quiet
        normalized_mode = mode.lower() if mode else self.LIGHTWEIGHT
        if normalized_mode not in self._VALID_MODES:
            normalized_mode = self.LIGHTWEIGHT
        self.install_mode = normalized_mode
        self.root_dir = root_dir or self._detect_git_root()
        self.hooks_dir = self.root_dir / ".git" / "hooks"
        self.templates_dir = Path(__file__).parent / "templates"

        # Colors for output
        self.RED = "\033[0;31m"
        self.GREEN = "\033[0;32m"
        self.YELLOW = "\033[1;33m"
        self.BLUE = "\033[0;34m"
        self.NC = "\033[0m"

    def _detect_git_root(self) -> Path:
        """Detect the Git repository root directory."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            )
            return Path(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fall back to current directory
            return Path.cwd()

    def _print_info(self, message: str) -> None:
        """Print info message (respecting quiet mode)."""
        if not self.quiet:
            print(message)

    def _print_success(self, message: str) -> None:
        """Print success message (respecting quiet mode)."""
        if not self.quiet:
            print(f"{self.GREEN}{message}{self.NC}")

    def _print_warning(self, message: str) -> None:
        """Print warning message (always shown)."""
        print(f"{self.YELLOW}{message}{self.NC}")

    def _print_error(self, message: str) -> None:
        """Print error message (always shown)."""
        print(f"{self.RED}{message}{self.NC}", file=sys.stderr)

    def _check_git_repo(self) -> bool:
        """Check if we're in a Git repository."""
        git_dir = self.root_dir / ".git"
        if not git_dir.exists():
            self._print_error("❌ 错误: 不在 Git 仓库中")
            return False
        return True

    def _backup_existing_hook(self, hook_path: Path) -> None:
        """Backup existing hook if it exists and is not a symlink."""
        # Check if it's a broken symlink
        if hook_path.is_symlink() and not hook_path.exists():
            # It's a broken symlink, just remove it
            hook_path.unlink()
            self._print_warning(f"⚠️  删除损坏的符号链接: {hook_path.name}")
            return

        if hook_path.exists() and not hook_path.is_symlink():
            from datetime import datetime

            backup_name = f"{hook_path.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = hook_path.parent / backup_name
            self._print_warning(f"⚠️  备份现有 {hook_path.name} hook 到: {backup_name}")
            hook_path.rename(backup_path)

    def _install_pre_commit_hook(self) -> bool:
        """Install the pre-commit hook."""
        self._print_info("")
        self._print_info("📦 安装 pre-commit hook...")

        pre_commit_template = self.templates_dir / "pre-commit"
        pre_commit_dst = self.hooks_dir / "pre-commit"

        if not pre_commit_template.exists():
            self._print_error(f"❌ 错误: 找不到 pre-commit 模板文件: {pre_commit_template}")
            return False

        # Ensure hooks directory exists
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        # Remove any existing hook (including broken symlinks)
        if pre_commit_dst.exists() or pre_commit_dst.is_symlink():
            self._backup_existing_hook(pre_commit_dst)

        # Copy the template
        import shutil

        shutil.copy2(pre_commit_template, pre_commit_dst)
        pre_commit_dst.chmod(0o755)

        self._print_success("✅ pre-commit hook 已安装")
        return True

    def _install_pre_commit_framework(self) -> bool:
        """Install and configure the pre-commit framework."""
        self._print_info("")
        self._print_info("📦 检查 pre-commit 框架...")

        # Check if pre-commit is available
        try:
            subprocess.run(
                ["pre-commit", "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._print_warning("⚠️  pre-commit 未安装")
            self._print_info("   代码质量检查将被跳过")
            self._print_info("   安装: pip install pre-commit")
            return False

        # Install hooks
        if self.install_mode == self.LIGHTWEIGHT:
            self._print_info(
                "   pre-commit 已安装，使用轻量级模式配置 hooks (首次提交时再下载工具链)..."
            )
        else:
            self._print_info("   pre-commit 已安装，配置完整 hooks...")
        pre_commit_config = self.root_dir / "tools" / "pre-commit-config.yaml"

        if not pre_commit_config.exists():
            self._print_warning(f"⚠️  未找到 pre-commit 配置文件: {pre_commit_config}")
            return False

        install_cmd = [
            "pre-commit",
            "install",
            "--config",
            str(pre_commit_config),
        ]
        if self.install_mode == self.FULL:
            install_cmd.append("--install-hooks")
        else:
            self._print_info("   将在首次 git commit 时自动下载所有 hook 依赖")

        try:
            subprocess.run(
                install_cmd,
                cwd=str(self.root_dir),
                capture_output=True,
                check=True,
            )
            self._print_success("✅ pre-commit 框架已配置")
            return True
        except subprocess.CalledProcessError:
            self._print_warning("⚠️  pre-commit 框架配置失败")
            return False

    def _test_architecture_checker(self) -> bool:
        """Test if architecture checker is available."""
        if not self.quiet:
            self._print_info("")
            self._print_info("🧪 测试 architecture checker...")

        # Try using sage-dev command first
        try:
            subprocess.run(
                ["sage-dev", "check-architecture", "--help"],
                capture_output=True,
                check=True,
            )
            if not self.quiet:
                self._print_success("✅ Architecture checker 可用 (sage-dev)")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Try Python module import
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from sage.dev.impl.tools.architecture_checker import ArchitectureChecker",
                ],
                capture_output=True,
                check=True,
            )
            if not self.quiet:
                self._print_success("✅ Architecture checker 可用 (Python module)")
            return True
        except subprocess.CalledProcessError:
            if not self.quiet:
                self._print_warning("⚠️  Architecture checker 测试失败，但 hook 已安装")
                self._print_info("   您可能需要安装 sage-tools: pip install -e packages/sage-tools")
            return False

    def install(self) -> bool:
        """
        Install Git hooks.

        Returns:
            True if installation was successful, False otherwise.
        """
        self._print_info("🔧 安装 SAGE Git Hooks...")

        # Check if in Git repo
        if not self._check_git_repo():
            return False

        # Install pre-commit hook
        if not self._install_pre_commit_hook():
            return False

        # Install pre-commit framework
        self._install_pre_commit_framework()

        # Test architecture checker
        self._test_architecture_checker()

        # Print summary
        if not self.quiet:
            self._print_info("")
            self._print_info("=" * 70)
            self._print_success("✅ Git hooks 安装完成！")
            self._print_info("")
            self._print_info("以下功能已激活:")
            self._print_info("  • 代码质量检查: black, isort, ruff, mypy（需要 pre-commit）")
            self._print_info("  • Dev-notes 文档规范检查: 分类、元数据等")
            self._print_info("  • 架构合规性检查: 包依赖、导入路径等")
            if self.install_mode == self.LIGHTWEIGHT:
                self._print_info("")
                self._print_info(
                    "💡 当前为轻量级模式：首次运行 pre-commit 时会自动下载完整工具链。"
                )
            self._print_info("")
            self._print_info("使用方法:")
            self._print_info("  • 正常提交: git commit -m 'message'")
            self._print_info("  • 跳过检查: git commit --no-verify -m 'message'")
            self._print_info("  • 安装代码检查工具: pip install pre-commit")
            self._print_info("")
            self._print_info("相关文档:")
            self._print_info("  • 架构规范: docs/PACKAGE_ARCHITECTURE.md")
            self._print_info("  • 文档模板: docs/dev-notes/TEMPLATE.md")
            self._print_info("=" * 70)

        return True

    def uninstall(self) -> bool:
        """
        Uninstall Git hooks.

        Returns:
            True if uninstallation was successful, False otherwise.
        """
        self._print_info("🗑️  卸载 SAGE Git Hooks...")

        # Check if in Git repo
        if not self._check_git_repo():
            return False

        # Remove pre-commit hook
        pre_commit_hook = self.hooks_dir / "pre-commit"
        if pre_commit_hook.exists():
            pre_commit_hook.unlink()
            self._print_success("✅ pre-commit hook 已删除")
        else:
            self._print_info("ℹ️  pre-commit hook 不存在")

        # Uninstall pre-commit framework hooks (optional)
        try:
            subprocess.run(
                ["pre-commit", "uninstall"],
                cwd=str(self.root_dir),
                capture_output=True,
                check=False,
            )
            self._print_success("✅ pre-commit 框架 hooks 已卸载")
        except FileNotFoundError:
            pass

        self._print_success("✅ Git hooks 卸载完成！")
        return True

    def status(self) -> dict:
        """
        Check the status of installed hooks.

        Returns:
            Dictionary with hook status information.
        """
        status_info = {
            "git_repo": self._check_git_repo(),
            "pre_commit_hook_installed": False,
            "pre_commit_framework_installed": False,
            "architecture_checker_available": False,
            "devnotes_checker_available": False,
        }

        if not status_info["git_repo"]:
            return status_info

        # Check pre-commit hook
        pre_commit_hook = self.hooks_dir / "pre-commit"
        status_info["pre_commit_hook_installed"] = pre_commit_hook.exists()

        # Check pre-commit framework
        try:
            subprocess.run(
                ["pre-commit", "--version"],
                capture_output=True,
                check=True,
            )
            status_info["pre_commit_framework_installed"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            status_info["pre_commit_framework_installed"] = False

        # Check architecture checker
        try:
            subprocess.run(
                ["sage-dev", "check-architecture", "--help"],
                capture_output=True,
                check=True,
            )
            status_info["architecture_checker_available"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            status_info["architecture_checker_available"] = False

        # Check devnotes checker
        try:
            subprocess.run(
                ["sage-dev", "check-devnotes", "--help"],
                capture_output=True,
                check=True,
            )
            status_info["devnotes_checker_available"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            status_info["devnotes_checker_available"] = False

        return status_info

    def print_status(self) -> None:
        """Print the status of installed hooks in a human-readable format."""
        status = self.status()

        print("\n" + "=" * 70)
        print("📊 SAGE Git Hooks 状态")
        print("=" * 70)

        # Git repo status
        if status["git_repo"]:
            print(f"{self.GREEN}✅ Git 仓库: 是{self.NC}")
        else:
            print(f"{self.RED}❌ Git 仓库: 否{self.NC}")
            print("\n" + "=" * 70)
            return

        # Pre-commit hook
        if status["pre_commit_hook_installed"]:
            print(f"{self.GREEN}✅ Pre-commit Hook: 已安装{self.NC}")
        else:
            print(f"{self.YELLOW}⚠️  Pre-commit Hook: 未安装{self.NC}")

        # Pre-commit framework
        if status["pre_commit_framework_installed"]:
            print(f"{self.GREEN}✅ Pre-commit 框架: 已安装{self.NC}")
        else:
            print(f"{self.YELLOW}⚠️  Pre-commit 框架: 未安装{self.NC}")
            print(f"   {self.BLUE}安装: pip install pre-commit{self.NC}")

        # Architecture checker
        if status["architecture_checker_available"]:
            print(f"{self.GREEN}✅ Architecture Checker: 可用{self.NC}")
        else:
            print(f"{self.YELLOW}⚠️  Architecture Checker: 不可用{self.NC}")
            print(f"   {self.BLUE}安装: pip install -e packages/sage-tools{self.NC}")

        # Devnotes checker
        if status["devnotes_checker_available"]:
            print(f"{self.GREEN}✅ DevNotes Checker: 可用{self.NC}")
        else:
            print(f"{self.YELLOW}⚠️  DevNotes Checker: 不可用{self.NC}")
            print(f"   {self.BLUE}安装: pip install -e packages/sage-tools{self.NC}")

        print("\n" + "=" * 70)

        # Recommendations
        if not all(
            [
                status["pre_commit_hook_installed"],
                status["pre_commit_framework_installed"],
                status["architecture_checker_available"],
            ]
        ):
            print("\n💡 建议:")
            if not status["pre_commit_hook_installed"]:
                print(
                    f"   {self.BLUE}• 运行 'sage-dev maintain hooks install' 安装 Git hooks{self.NC}"
                )
            if not status["pre_commit_framework_installed"]:
                print(
                    f"   {self.BLUE}• 运行 'pip install pre-commit' 安装代码质量检查工具{self.NC}"
                )
            print("")
