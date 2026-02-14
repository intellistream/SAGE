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
6. 根目录文件规范（避免临时/测试文件污染根目录）

NOTE: sage-llm-core and sage-llm-gateway have been migrated to isagellm.
      LLM functionality is now via: pip install isagellm
"""

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ============================================================================
# 架构定义
# ============================================================================

# 包的层级定义（根据 PACKAGE_ARCHITECTURE.md）
# NOTE: sage-apps, sage-benchmark, sage-studio 已迁移到独立仓库，不再包含在此检查中
LAYER_DEFINITION = {
    "L1": ["sage-common"],
    "L2": ["sage-platform"],
    "L3": ["sage-kernel", "sage-libs"],
    "L4": ["sage-middleware"],
    "L5": [],  # sage-apps, sage-benchmark 已迁移到独立仓库
    "L6": ["sage-tools"],  # sage-studio 已迁移到独立仓库
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
    "sage-kernel": {"sage-common", "sage-platform"},  # L3 kernel 独立，不依赖 libs
    "sage-libs": {"sage-common", "sage-platform"},  # L3 libs 独立，不依赖 kernel
    "sage-middleware": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
    },  # L4 -> L3, L2, L1
    # NOTE: sage-apps, sage-benchmark, sage-studio 已迁移到独立仓库
    "sage-tools": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
        "sage-studio",
    },  # L6 -> L5(studio), L4, L3, L2, L1
    "sage-llm-gateway": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
        "sage-studio",  # Gateway 集成 Studio Backend 路由
    },  # L6 -> L6(studio), L4, L3, L2, L1
}

# 包的根目录映射
# NOTE: sage-apps, sage-benchmark, sage-studio 已迁移到独立仓库
PACKAGE_PATHS = {
    "sage-common": "packages/sage-common/src",
    "sage-platform": "packages/sage-platform/src",
    "sage-kernel": "packages/sage-kernel/src",
    "sage-libs": "packages/sage-libs/src",
    "sage-middleware": "packages/sage-middleware/src",
    "sage-tools": "packages/sage-tools/src",
}

# 包名到 Python 模块路径的映射（处理共享命名空间的情况）
# 大多数包: sage-xxx -> sage/xxx
# NOTE: sage-apps, sage-benchmark, sage-studio 已迁移到独立仓库
PACKAGE_MODULE_PATHS = {
    "sage-common": "sage/common",
    "sage-platform": "sage/platform",
    "sage-kernel": "sage/kernel",
    "sage-libs": "sage/libs",
    "sage-middleware": "sage/middleware",
    "sage-tools": "sage/tools",
}

# Submodules to exclude from checks (maintained in separate repositories)
SUBMODULE_PATHS = {
    "sageLLM",
    "sageVDB",
    "sageFlow",
    "neuromem",
    "sageTSDB",
    "docs-public",
}

# 模块职责规则：定义哪些模块类型应该在哪一层
# 格式：(pattern, expected_layer, description, suggestion)
MODULE_RESPONSIBILITY_RULES = [
    # Pipeline/Orchestration 层 - 应该在 middleware 或更高层
    (
        r".*/(pipeline|orchestration|workflow)\.py$",
        ["L4", "L5", "L6"],
        "Pipeline/Orchestration 模块（编排层）",
        "Pipeline 编排多个算子，应该在 sage-middleware (L4) 或更高层",
    ),
    # Profiler/Monitor - 如果是算子应该在 middleware
    (
        r".*/(profiler|monitor)\.py$",
        ["L4", "L5", "L6"],
        "Profiler/Monitor 模块",
        "如果是算子实现（继承 MapFunction/FilterFunction），应该在 sage-middleware (L4)",
    ),
    # Operators - 具体的算子实现应该在 middleware
    (
        r".*/operators/.+\.py$",
        ["L4", "L5", "L6"],
        "Operator 实现",
        "具体的算子实现应该在 sage-middleware (L4) 或应用层",
    ),
]

# 根目录允许的文件（不区分大小写）
# 只列出项目标准文件，其他文件都应该放在对应的子目录
ALLOWED_ROOT_FILES = {
    # 文档文件
    "readme.md",
    "contributing.md",
    "developer.md",
    "license",
    "license.md",
    "changelog.md",
    "code_of_conduct.md",
    "security.md",
    # 配置文件
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".flake8",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "makefile",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".dockerignore",
    "codecov.yml",
    ".codecov.yml",
    # 依赖管理
    "dependencies-spec.yaml",  # 统一依赖版本规范
    # Shell 脚本
    "manage.sh",
    "quickstart.sh",
    # VS Code workspace files
    "sage.code-workspace",
    "sagellm.code-workspace",
    "sage-studio.code-workspace",
    # 其他
    "cmakelists.txt",
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
    suggestion: str | None = None  # 修复建议


@dataclass
class CheckResult:
    """检查结果"""

    passed: bool
    violations: list[ArchitectureViolation] = field(default_factory=list)
    warnings: list[ArchitectureViolation] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


# ============================================================================
# AST 解析器
# ============================================================================


class ImportExtractor(ast.NodeVisitor):
    """提取 Python 文件中的所有导入语句"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.imports: list[ImportStatement] = []
        self.in_type_checking = False  # 跟踪是否在 TYPE_CHECKING 块中

    def visit_If(self, node: ast.If):
        """检查是否进入 TYPE_CHECKING 块"""
        # 检查条件是否是 TYPE_CHECKING
        is_type_checking_block = False
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            is_type_checking_block = True

        if is_type_checking_block:
            # 暂时设置标志，访问 if 块内容，然后恢复
            old_value = self.in_type_checking
            self.in_type_checking = True
            for child in node.body:
                self.visit(child)
            self.in_type_checking = old_value
            # 访问 else 块（如果有）
            for child in node.orelse:
                self.visit(child)
        else:
            # 正常访问
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        # 忽略 TYPE_CHECKING 块中的导入
        if not self.in_type_checking:
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
        # 忽略 TYPE_CHECKING 块中的导入
        if not self.in_type_checking and node.module:
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

    def __init__(self, root_dir: Path | str):
        self.root_dir = Path(root_dir) if isinstance(root_dir, str) else root_dir
        self.violations: list[ArchitectureViolation] = []
        self.warnings: list[ArchitectureViolation] = []

    def extract_package_name(self, filepath: Path) -> str | None:
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

    def get_imported_package(self, module_name: str) -> str | None:
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
        """检查内部导入是否使用公共 API

        只对跨包的内部导入发出警告，同包内的内部导入是允许的。
        """
        module = import_info.module

        # 获取被导入模块所属的包
        target_pkg = self.get_imported_package(module)

        # 如果是同一个包内的导入，不检查（同包内可以随意导入）
        if target_pkg == source_pkg:
            return

        # 只对跨包的内部导入进行检查
        # 检查是否直接导入了内部模块
        internal_patterns = [
            (r"sage\.\w+\.runtime\.", "runtime"),  # 直接导入 runtime 内部
            (
                r"sage\.\w+\.core\.(?!__init__)",
                "core子模块",
            ),  # 直接导入 core 子模块（如 core.functions）
            (r"sage\.\w+\._", "私有模块"),  # 私有模块
        ]

        for pattern, module_type in internal_patterns:
            if re.match(pattern, module):
                # 为 core 子模块提供更具体的建议
                if "core" in module_type and ".core." in module:
                    # 提取包名，例如从 sage.common.core.functions 提取 sage.common.core
                    parts = module.split(".")
                    if len(parts) >= 3:
                        public_api = ".".join(parts[:3])  # sage.common.core
                        suggestion = f"建议从公共 API 导入: from {public_api} import ..."
                    else:
                        suggestion = f"建议使用 {target_pkg} 的公共 API 进行导入。"
                else:
                    suggestion = (
                        f"建议使用 {target_pkg} 的公共 API，避免依赖内部实现（{module_type}）。"
                    )

                self.warnings.append(
                    ArchitectureViolation(
                        type="INTERNAL_IMPORT",
                        severity="WARNING",
                        file=import_info.file,
                        line=import_info.line,
                        message=f"跨包导入内部模块: {module}（从 {source_pkg} 到 {target_pkg}）",
                        suggestion=suggestion,
                    )
                )
                break

    def check_file_imports(self, filepath: Path) -> list[ImportStatement]:
        """检查单个文件的导入"""
        try:
            with open(filepath, encoding="utf-8") as f:
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
        module_path = PACKAGE_MODULE_PATHS.get(package_name, package_name.replace("sage-", "sage/"))
        init_file = package_path / module_path / "__init__.py"
        if not init_file.exists():
            self.warnings.append(
                ArchitectureViolation(
                    type="MISSING_INIT",
                    severity="WARNING",
                    file=init_file,
                    line=0,
                    message="缺少 __init__.py，可能影响包导入",
                )
            )

        return True

    def check_layer_marker(self, package_name: str) -> bool:
        """检查包是否包含 Layer 标记"""
        package_path = self.root_dir / PACKAGE_PATHS[package_name]
        module_path = PACKAGE_MODULE_PATHS.get(package_name, package_name.replace("sage-", "sage/"))
        init_file = package_path / module_path / "__init__.py"

        if not init_file.exists():
            return False

        try:
            with open(init_file, encoding="utf-8") as f:
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
                        message="缺少 __layer__ 标记",
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

    def check_module_responsibility(self, filepath: Path) -> bool:
        """检查模块是否在正确的层级

        某些类型的模块（如 pipeline, orchestration）应该只出现在特定层级。
        """
        # 获取文件所属的包
        source_pkg = self.extract_package_name(filepath)
        if not source_pkg:
            return True

        source_layer = PACKAGE_TO_LAYER.get(source_pkg, "Unknown")
        if source_layer == "Unknown":
            return True

        # 检查文件路径是否匹配任何规则
        file_path_str = str(filepath)

        for pattern, allowed_layers, module_type, suggestion in MODULE_RESPONSIBILITY_RULES:
            if re.search(pattern, file_path_str):
                # 检查当前层级是否允许
                if source_layer not in allowed_layers:
                    # 检查文件内容以确认是否真的是该类型的模块
                    if self._confirm_module_type(filepath, module_type):
                        self.violations.append(
                            ArchitectureViolation(
                                type="MODULE_MISPLACEMENT",
                                severity="ERROR",
                                file=filepath,
                                line=0,
                                message=f"{module_type} 位于错误的层级: {source_pkg} ({source_layer})",
                                suggestion=suggestion,
                            )
                        )
                        return False

        return True

    def _confirm_module_type(self, filepath: Path, module_type: str) -> bool:
        """通过分析文件内容确认模块类型

        避免误报：只有真正符合特征的模块才算违规。
        """
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            # Pipeline/Orchestration - 检查是否有编排逻辑
            if "Pipeline" in module_type or "Orchestration" in module_type:
                # 查找 Pipeline 类定义或编排相关代码
                if re.search(r"class \w*Pipeline", content):
                    return True
                if re.search(r"def (orchestrate|run|execute).*pipeline", content, re.IGNORECASE):
                    return True

            # Profiler/Monitor - 检查是否继承算子基类
            if "Profiler" in module_type or "Monitor" in module_type:
                # 查找是否继承 Function 类
                if re.search(r"class \w+\((Map|Filter|Batch|Sink)Function\)", content):
                    return True
                # 或者有 execute 方法
                if re.search(r"class \w+Profiler.*:.*def execute", content, re.DOTALL):
                    return True

            # Operator 实现 - 检查是否在 operators 目录且实现了算子
            if "Operator" in module_type:
                if "operators/" in str(filepath):
                    # 检查是否继承算子基类
                    if re.search(
                        r"class \w+\((Map|Filter|Batch|Sink|Operator|Function)\)", content
                    ):
                        return True

        except Exception:
            # 如果无法读取文件，保守地返回 False（不报错）
            pass

        return False

    def check_root_directory_files(self) -> bool:
        """检查根目录文件是否符合规范

        返回:
            bool: True 表示通过，False 表示有问题
        """
        if not self.root_dir.exists():
            return True

        issues_found = False

        # 获取根目录下所有 git 跟踪的文件（不包括子目录）
        import subprocess

        try:
            # 使用 git ls-files 只获取 git 跟踪的文件
            result = subprocess.run(
                ["git", "ls-files", "--cached"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # 过滤出根目录的文件（不包含 / 的文件名）
            git_files = [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip() and "/" not in line.strip()
            ]

            root_files = [
                self.root_dir / filename
                for filename in git_files
                if (self.root_dir / filename).is_file()
            ]

        except subprocess.CalledProcessError:
            # 如果不是 git 仓库，回退到检查所有文件
            root_files = [f for f in self.root_dir.iterdir() if f.is_file()]

        # 检查每个文件
        for file_path in root_files:
            filename = file_path.name.lower()

            # 跳过隐藏文件（以 . 开头）
            if filename.startswith("."):
                # 检查是否在允许列表中
                if filename not in ALLOWED_ROOT_FILES:
                    # 隐藏配置文件通常是可以接受的，只给警告
                    continue
                else:
                    continue

            # 检查是否在允许列表中
            if filename not in ALLOWED_ROOT_FILES:
                # 根据文件类型给出具体建议
                suggestion = self._get_file_placement_suggestion(file_path)

                self.violations.append(
                    ArchitectureViolation(
                        type="INVALID_ROOT_FILE",
                        severity="ERROR",
                        file=file_path,
                        line=0,
                        message=f"根目录不应包含此文件: {file_path.name}",
                        suggestion=suggestion,
                    )
                )
                issues_found = True

        return not issues_found

    def _get_file_placement_suggestion(self, file_path: Path) -> str:
        """根据文件类型提供放置建议"""
        filename = file_path.name.lower()
        suffix = file_path.suffix.lower()

        # Python 测试文件
        if filename.startswith("test_") and suffix == ".py":
            return "测试文件应该放在: packages/sage-tools/tests/ 或对应包的 tests/ 目录下"

        # Python 脚本
        if suffix == ".py":
            return (
                "Python 脚本应该放在: tools/ (系统脚本) 或 packages/sage-tools/scripts/ (开发工具)"
            )

        # Markdown 文档
        if suffix == ".md":
            if any(kw in filename for kw in ["migration", "cleanup", "refactor", "tools"]):
                return "开发文档应该放在: docs/dev-notes/l5-tools/ 或相应的分类目录下"
            else:
                return (
                    "文档应该放在: docs/dev-notes/ (开发笔记) 或 docs-public/docs_src/ (公开文档)"
                )

        # 配置文件
        if suffix in [".yml", ".yaml", ".json", ".toml", ".ini", ".cfg"]:
            return "配置文件应该放在: 项目根目录的隐藏文件（如 .codecov.yml）或 tools/ 目录下"

        # Shell 脚本
        if suffix == ".sh":
            return "Shell 脚本应该放在: tools/ 目录下"

        # 数据文件
        if suffix in [".csv", ".json", ".txt", ".dat"]:
            return "数据文件应该放在: examples/data/ 或 packages/*/tests/data/"

        return "请将文件移动到合适的子目录中"

    def check_all(self) -> CheckResult:
        """检查所有文件"""
        return self.run_checks(changed_files=None)

    def check_changed_files(self, diff_target: str = "HEAD") -> CheckResult:
        """检查 Git 变更的文件"""
        changed_files = get_changed_files(diff_target)
        if not changed_files:
            # 没有变更文件，返回通过
            return CheckResult(
                passed=True,
                violations=[],
                warnings=[],
                stats={"total_files": 0, "total_imports": 0},
            )
        return self.run_checks(changed_files=changed_files)

    def run_checks(self, changed_files: list[Path] | None = None) -> CheckResult:
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
                    for py_file in full_path.rglob("*.py"):
                        # 排除 submodules 中的文件
                        if not any(submodule in py_file.parts for submodule in SUBMODULE_PATHS):
                            files_to_check.append(py_file)
            print(f"📝 检查全部 {len(files_to_check)} 个 Python 文件 (排除 submodules)")

        # 过滤掉 submodules 中的文件（如果是 changed_files 模式）
        if changed_files:
            original_count = len(files_to_check)
            files_to_check = [
                f
                for f in files_to_check
                if not any(submodule in f.parts for submodule in SUBMODULE_PATHS)
            ]
            if len(files_to_check) < original_count:
                print(f"⏭️  排除了 {original_count - len(files_to_check)} 个 submodule 文件")

        # 统计信息
        stats = {
            "total_files": len(files_to_check),
            "total_imports": 0,
            "illegal_dependencies": 0,
            "internal_imports": 0,
            "missing_markers": 0,
            "module_misplacements": 0,
        }

        # 1. 检查模块职责边界
        print("\n1️⃣  检查模块职责边界...")
        for filepath in files_to_check:
            if not self.check_module_responsibility(filepath):
                stats["module_misplacements"] += 1

        # 2. 检查导入依赖
        print("\n2️⃣  检查包依赖关系...")
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

        # 3. 检查包结构
        print("3️⃣  检查包结构...")
        for package_name in PACKAGE_PATHS.keys():
            self.check_package_structure(package_name)

        # 4. 检查 Layer 标记
        print("4️⃣  检查 Layer 标记...")
        for package_name in PACKAGE_PATHS.keys():
            if not self.check_layer_marker(package_name):
                stats["missing_markers"] += 1

        # 5. 检查根目录文件
        print("5️⃣  检查根目录文件规范...")
        root_files_ok = self.check_root_directory_files()
        if not root_files_ok:
            stats["invalid_root_files"] = len(
                [v for v in self.violations if v.type == "INVALID_ROOT_FILE"]
            )

        stats["internal_imports"] = len([v for v in self.warnings if v.type == "INTERNAL_IMPORT"])

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
    print(f"  • 模块位置错误: {result.stats.get('module_misplacements', 0)}")
    print(f"  • 内部导入: {result.stats['internal_imports']}")
    print(f"  • 缺少标记: {result.stats['missing_markers']}")
    if "invalid_root_files" in result.stats:
        print(f"  • 根目录问题文件: {result.stats['invalid_root_files']}")

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


def get_changed_files(git_diff: str = "HEAD") -> list[Path]:
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

    parser = argparse.ArgumentParser(description="SAGE Architecture Compliance Checker")
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
