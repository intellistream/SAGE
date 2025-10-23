#!/usr/bin/env python3
"""
SAGE Architecture Compliance Checker

检测代码是否符合 SAGE 系统架构设计规范。

用途:
- CI/CD 自动化检测
- 本地开发前检查
- PR 审查辅助

检查项:
1. 包依赖规则（Layer 分层架构）
2. 导入路径合规性
3. 模块结构规范
4. 公共 API 导出
5. 架构标记完整性
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import re

# ============================================================================
# 架构定义
# ============================================================================

# 包的层级定义（根据 PACKAGE_ARCHITECTURE.md）
LAYER_DEFINITION = {
    "L1": ["sage-common"],
    "L2": ["sage-platform"],
    "L3": ["sage-kernel", "sage-libs"],
    "L4": ["sage-middleware"],
    "L5": ["sage-apps", "sage-benchmark"],
    "L6": ["sage-studio", "sage-tools"],
}

# 反向映射：包名 -> 层级
PACKAGE_TO_LAYER = {}
for layer, packages in LAYER_DEFINITION.items():
    for pkg in packages:
        PACKAGE_TO_LAYER[pkg] = layer

# 允许的依赖关系（高层 -> 低层）
ALLOWED_DEPENDENCIES = {
    "sage-common": set(),  # L1 不依赖任何包
    "sage-platform": {"sage-common"},  # L2 -> L1
    "sage-kernel": {"sage-common", "sage-platform"},  # L3 -> L2, L1
    "sage-libs": {"sage-common", "sage-platform", "sage-kernel"},  # L3 -> L2, L1, L3
    "sage-middleware": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
    },  # L4 -> L3, L2, L1
    "sage-apps": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
    },  # L5 -> L4, L3, L2, L1
    "sage-benchmark": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
    },  # L5 -> L4, L3, L2, L1
    "sage-studio": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
    },  # L6 -> L4, L3, L2, L1
    "sage-tools": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
        "sage-studio",
    },  # L6 -> L5(studio), L4, L3, L2, L1
}

# 包的根目录映射
PACKAGE_PATHS = {
    "sage-common": "packages/sage-common/src",
    "sage-platform": "packages/sage-platform/src",
    "sage-kernel": "packages/sage-kernel/src",
    "sage-libs": "packages/sage-libs/src",
    "sage-middleware": "packages/sage-middleware/src",
    "sage-apps": "packages/sage-apps/src",
    "sage-benchmark": "packages/sage-benchmark/src",
    "sage-studio": "packages/sage-studio/src",
    "sage-tools": "packages/sage-tools/src",
}


# ============================================================================
# 数据结构
# ============================================================================


@dataclass
class ImportStatement:
    """导入语句信息"""

    module: str  # 导入的模块名
    file: Path  # 所在文件
    line: int  # 行号
    statement: str  # 原始语句


@dataclass
class ArchitectureViolation:
    """架构违规"""

    type: str  # 违规类型
    severity: str  # 严重程度: ERROR, WARNING, INFO
    file: Path  # 文件路径
    line: int  # 行号
    message: str  # 详细信息
    suggestion: Optional[str] = None  # 修复建议


@dataclass
class CheckResult:
    """检查结果"""

    passed: bool
    violations: List[ArchitectureViolation] = field(default_factory=list)
    warnings: List[ArchitectureViolation] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)


# ============================================================================
# AST 解析器
# ============================================================================


class ImportExtractor(ast.NodeVisitor):
    """提取 Python 文件中的所有导入语句"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.imports: List[ImportStatement] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(
                ImportStatement(
                    module=alias.name,
                    file=self.filepath,
                    line=node.lineno,
                    statement=f"import {alias.name}",
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(
                ImportStatement(
                    module=node.module,
                    file=self.filepath,
                    line=node.lineno,
                    statement=f"from {node.module} import ...",
                )
            )
        self.generic_visit(node)


# ============================================================================
# 架构检查器
# ============================================================================


class ArchitectureChecker:
    """架构合规性检查器"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.violations: List[ArchitectureViolation] = []
        self.warnings: List[ArchitectureViolation] = []

    def extract_package_name(self, filepath: Path) -> Optional[str]:
        """从文件路径提取包名"""
        try:
            rel_path = filepath.relative_to(self.root_dir)
            path_str = str(rel_path)

            # 匹配 packages/sage-xxx/
            match = re.match(r"packages/(sage-[^/]+)/", path_str)
            if match:
                return match.group(1)
        except ValueError:
            pass
        return None

    def get_imported_package(self, module_name: str) -> Optional[str]:
        """从导入语句中提取被导入的包名"""
        # sage.common.xxx -> sage-common
        # sage.kernel.xxx -> sage-kernel
        if module_name.startswith("sage."):
            parts = module_name.split(".")
            if len(parts) >= 2:
                submodule = parts[1]
                # 特殊处理：将下划线转换为连字符
                return f"sage-{submodule}"
        return None

    def check_layer_dependency(
        self, source_pkg: str, target_pkg: str, import_info: ImportStatement
    ) -> bool:
        """检查层级依赖是否合规"""
        if source_pkg == target_pkg:
            return True  # 同包内导入总是允许的

        allowed = ALLOWED_DEPENDENCIES.get(source_pkg, set())
        if target_pkg not in allowed:
            source_layer = PACKAGE_TO_LAYER.get(source_pkg, "Unknown")
            target_layer = PACKAGE_TO_LAYER.get(target_pkg, "Unknown")

            self.violations.append(
                ArchitectureViolation(
                    type="ILLEGAL_DEPENDENCY",
                    severity="ERROR",
                    file=import_info.file,
                    line=import_info.line,
                    message=f"非法依赖: {source_pkg} ({source_layer}) -> {target_pkg} ({target_layer})",
                    suggestion=f"请检查 PACKAGE_ARCHITECTURE.md 中的依赖规则。"
                    f"{source_layer} 层不应该依赖 {target_layer} 层的包。",
                )
            )
            return False

        return True

    def check_internal_import(self, import_info: ImportStatement, source_pkg: str):
        """检查内部导入是否使用公共 API"""
        module = import_info.module

        # 检查是否直接导入了内部模块
        internal_patterns = [
            r"sage\.\w+\.runtime\.",  # 直接导入 runtime 内部
            r"sage\.\w+\.core\.",  # 直接导入 core 内部（非公共 API）
            r"sage\.\w+\._",  # 私有模块
        ]

        for pattern in internal_patterns:
            if re.match(pattern, module):
                self.warnings.append(
                    ArchitectureViolation(
                        type="INTERNAL_IMPORT",
                        severity="WARNING",
                        file=import_info.file,
                        line=import_info.line,
                        message=f"直接导入内部模块: {module}",
                        suggestion="建议使用包的公共 API 进行导入。",
                    )
                )
                break

    def check_file_imports(self, filepath: Path) -> List[ImportStatement]:
        """检查单个文件的导入"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(filepath))

            extractor = ImportExtractor(filepath)
            extractor.visit(tree)
            return extractor.imports
        except SyntaxError as e:
            self.warnings.append(
                ArchitectureViolation(
                    type="SYNTAX_ERROR",
                    severity="WARNING",
                    file=filepath,
                    line=e.lineno or 0,
                    message=f"语法错误，跳过检查: {e}",
                )
            )
            return []
        except Exception as e:
            self.warnings.append(
                ArchitectureViolation(
                    type="PARSE_ERROR",
                    severity="WARNING",
                    file=filepath,
                    line=0,
                    message=f"解析错误，跳过检查: {e}",
                )
            )
            return []

    def check_package_structure(self, package_name: str) -> bool:
        """检查包结构是否规范"""
        package_path = self.root_dir / PACKAGE_PATHS[package_name]

        if not package_path.exists():
            self.violations.append(
                ArchitectureViolation(
                    type="MISSING_PACKAGE",
                    severity="ERROR",
                    file=package_path,
                    line=0,
                    message=f"包目录不存在: {package_path}",
                )
            )
            return False

        # 检查 __init__.py 是否存在
        init_file = package_path / "sage" / package_name.replace("sage-", "") / "__init__.py"
        if not init_file.exists():
            self.warnings.append(
                ArchitectureViolation(
                    type="MISSING_INIT",
                    severity="WARNING",
                    file=init_file,
                    line=0,
                    message=f"缺少 __init__.py，可能影响包导入",
                )
            )

        return True

    def check_layer_marker(self, package_name: str) -> bool:
        """检查包是否包含 Layer 标记"""
        package_path = self.root_dir / PACKAGE_PATHS[package_name]
        init_file = package_path / "sage" / package_name.replace("sage-", "") / "__init__.py"

        if not init_file.exists():
            return False

        try:
            with open(init_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找 __layer__ 定义
            if "__layer__" not in content:
                expected_layer = PACKAGE_TO_LAYER.get(package_name, "Unknown")
                self.warnings.append(
                    ArchitectureViolation(
                        type="MISSING_LAYER_MARKER",
                        severity="WARNING",
                        file=init_file,
                        line=0,
                        message=f"缺少 __layer__ 标记",
                        suggestion=f"在 __init__.py 中添加: __layer__ = '{expected_layer}'",
                    )
                )
                return False

        except Exception as e:
            self.warnings.append(
                ArchitectureViolation(
                    type="CHECK_ERROR",
                    severity="WARNING",
                    file=init_file,
                    line=0,
                    message=f"无法检查 Layer 标记: {e}",
                )
            )
            return False

        return True

    def run_checks(
        self, changed_files: Optional[List[Path]] = None
    ) -> CheckResult:
        """运行所有检查"""
        print("🔍 开始架构合规性检查...\n")

        # 如果指定了文件列表，只检查这些文件
        if changed_files:
            files_to_check = changed_files
            print(f"📝 检查 {len(files_to_check)} 个变更文件")
        else:
            # 否则检查所有 Python 文件
            files_to_check = []
            for pkg_path in PACKAGE_PATHS.values():
                full_path = self.root_dir / pkg_path
                if full_path.exists():
                    files_to_check.extend(full_path.rglob("*.py"))
            print(f"📝 检查全部 {len(files_to_check)} 个 Python 文件")

        # 统计信息
        stats = {
            "total_files": len(files_to_check),
            "total_imports": 0,
            "illegal_dependencies": 0,
            "internal_imports": 0,
            "missing_markers": 0,
        }

        # 1. 检查导入依赖
        print("\n1️⃣  检查包依赖关系...")
        for filepath in files_to_check:
            if filepath.name == "__init__.py" or filepath.suffix != ".py":
                continue

            source_pkg = self.extract_package_name(filepath)
            if not source_pkg:
                continue

            imports = self.check_file_imports(filepath)
            stats["total_imports"] += len(imports)

            for imp in imports:
                target_pkg = self.get_imported_package(imp.module)
                if target_pkg and target_pkg in PACKAGE_TO_LAYER:
                    # 检查层级依赖
                    if not self.check_layer_dependency(source_pkg, target_pkg, imp):
                        stats["illegal_dependencies"] += 1

                    # 检查内部导入
                    self.check_internal_import(imp, source_pkg)

        # 2. 检查包结构
        print("2️⃣  检查包结构...")
        for package_name in PACKAGE_PATHS.keys():
            self.check_package_structure(package_name)

        # 3. 检查 Layer 标记
        print("3️⃣  检查 Layer 标记...")
        for package_name in PACKAGE_PATHS.keys():
            if not self.check_layer_marker(package_name):
                stats["missing_markers"] += 1

        stats["internal_imports"] = len(
            [v for v in self.warnings if v.type == "INTERNAL_IMPORT"]
        )

        # 生成结果
        result = CheckResult(
            passed=len(self.violations) == 0,
            violations=self.violations,
            warnings=self.warnings,
            stats=stats,
        )

        return result


# ============================================================================
# 报告生成
# ============================================================================


def print_report(result: CheckResult):
    """打印检查报告"""
    print("\n" + "=" * 80)
    print("📊 架构合规性检查报告")
    print("=" * 80)

    # 统计信息
    print("\n📈 统计信息:")
    print(f"  • 检查文件数: {result.stats['total_files']}")
    print(f"  • 导入语句数: {result.stats['total_imports']}")
    print(f"  • 非法依赖: {result.stats['illegal_dependencies']}")
    print(f"  • 内部导入: {result.stats['internal_imports']}")
    print(f"  • 缺少标记: {result.stats['missing_markers']}")

    # 错误列表
    if result.violations:
        print(f"\n❌ 发现 {len(result.violations)} 个架构违规:\n")
        for i, v in enumerate(result.violations, 1):
            print(f"{i}. [{v.severity}] {v.type}")
            print(f"   文件: {v.file}:{v.line}")
            print(f"   问题: {v.message}")
            if v.suggestion:
                print(f"   建议: {v.suggestion}")
            print()

    # 警告列表
    if result.warnings:
        print(f"\n⚠️  发现 {len(result.warnings)} 个警告:\n")
        for i, w in enumerate(result.warnings[:10], 1):  # 只显示前10个
            print(f"{i}. [{w.severity}] {w.type}")
            print(f"   文件: {w.file}:{w.line}")
            print(f"   问题: {w.message}")
            if w.suggestion:
                print(f"   建议: {w.suggestion}")
            print()

        if len(result.warnings) > 10:
            print(f"   ... 还有 {len(result.warnings) - 10} 个警告未显示\n")

    # 最终结果
    print("=" * 80)
    if result.passed:
        print("✅ 架构合规性检查通过！")
    else:
        print("❌ 架构合规性检查失败！")
        print(f"   发现 {len(result.violations)} 个必须修复的问题")

    print("=" * 80)


def get_changed_files(git_diff: str = "HEAD") -> List[Path]:
    """获取 Git 变更的文件列表"""
    import subprocess

    try:
        # 在 CI 中，通常检查与 main 分支的差异
        result = subprocess.run(
            ["git", "diff", "--name-only", git_diff],
            capture_output=True,
            text=True,
            check=True,
        )

        changed = []
        for line in result.stdout.strip().split("\n"):
            if line.endswith(".py"):
                path = Path(line)
                if path.exists():
                    changed.append(path)

        return changed
    except subprocess.CalledProcessError:
        return []


# ============================================================================
# 主程序
# ============================================================================


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="SAGE Architecture Compliance Checker"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="SAGE 项目根目录 (默认: 当前目录)",
    )
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="仅检查 Git 变更的文件",
    )
    parser.add_argument(
        "--diff",
        type=str,
        default="origin/main",
        help="Git diff 比较目标 (默认: origin/main)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：将警告也视为错误",
    )

    args = parser.parse_args()

    # 检查项目根目录
    root_dir = args.root.resolve()
    if not (root_dir / "packages").exists():
        print(f"❌ 错误: {root_dir} 不是有效的 SAGE 项目根目录")
        sys.exit(1)

    # 创建检查器
    checker = ArchitectureChecker(root_dir)

    # 确定要检查的文件
    changed_files = None
    if args.changed_only:
        changed_files = get_changed_files(args.diff)
        if not changed_files:
            print("ℹ️  没有 Python 文件变更，跳过检查")
            sys.exit(0)

    # 运行检查
    result = checker.run_checks(changed_files)

    # 打印报告
    print_report(result)

    # 返回状态码
    if not result.passed:
        sys.exit(1)

    if args.strict and result.warnings:
        print("\n⚠️  严格模式：存在警告，视为失败")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
