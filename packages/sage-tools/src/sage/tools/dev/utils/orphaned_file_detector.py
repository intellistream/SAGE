"""
SAGE 废弃文件检查器

检查项目中没有被其他文件引用的Python文件，帮助清理代码库。
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from sage.common.utils.formatting import format_size_compact


@dataclass
class OrphanedFile:
    """废弃文件信息"""

    path: Path
    relative_path: Path
    module_path: str
    size_bytes: int
    last_modified: float


class OrphanedFileDetector:
    """废弃文件检测器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.all_python_files = []
        self.exclude_patterns = {
            # 目录排除模式
            "__pycache__",
            ".pytest_cache",
            ".git",
            "site-packages",
            ".sage",
            "node_modules",
            # 文件排除模式
            "__init__.py",
            "conftest.py",
        }

    def get_all_python_files(self) -> list[Path]:
        """获取项目中所有Python文件"""
        python_files = []

        for root, dirs, files in os.walk(self.project_root):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in self.exclude_patterns]

            for file in files:
                if file.endswith(".py") and file not in self.exclude_patterns:
                    python_files.append(Path(root) / file)

        return python_files

    def extract_module_path(self, file_path: Path) -> str:
        """从文件路径提取模块导入路径"""
        try:
            rel_path = file_path.relative_to(self.project_root)
            parts = rel_path.parts

            # 找到src目录或直接使用packages目录
            if "src" in parts:
                src_index = parts.index("src")
                module_parts = parts[src_index + 1 :]
            elif "packages" in parts:
                pkg_index = parts.index("packages")
                module_parts = parts[pkg_index + 1 :]
            else:
                module_parts = parts

            # 移除.py扩展名
            if module_parts and module_parts[-1].endswith(".py"):
                module_parts = module_parts[:-1] + (module_parts[-1][:-3],)

            # 过滤掉__init__
            if module_parts and module_parts[-1] == "__init__":
                module_parts = module_parts[:-1]

            return ".".join(module_parts) if module_parts else ""

        except (ValueError, IndexError):
            return ""

    def find_imports_in_file(self, file_path: Path) -> set[str]:
        """在单个文件中查找所有导入"""
        imports = set()

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # 查找各种import语句
            patterns = [
                r"from\s+([\w\.]+)\s+import",  # from module import
                r"import\s+([\w\.]+)",  # import module
                r'importlib\.import_module\(["\']([^"\']+)["\']',  # 动态导入
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                imports.update(matches)

        except Exception:
            pass  # 忽略文件读取错误

        return imports

    def check_file_references(self, target_file: Path, all_files: list[Path]) -> list[str]:
        """检查文件是否被其他文件引用"""
        module_path = self.extract_module_path(target_file)
        if not module_path:
            return []

        references = []

        # 构建可能的引用模式
        possible_refs = [
            module_path,
            module_path.split(".")[-1],  # 只要最后一部分
            target_file.stem,  # 文件名
        ]

        for other_file in all_files:
            if other_file == target_file:
                continue

            imports = self.find_imports_in_file(other_file)

            # 检查是否有匹配的导入
            for ref in possible_refs:
                if any(ref in imp or imp.endswith(ref) for imp in imports):
                    references.append(str(other_file.relative_to(self.project_root)))
                    break

        return references

    def detect_orphaned_files(
        self, check_directories: list[str] | None = None
    ) -> list[OrphanedFile]:
        """检测废弃文件"""
        if check_directories is None:
            check_directories = [
                "packages/sage-tools/src/sage/tools/dev/tools",
                "packages/sage-tools/src/sage/tools/dev/utils",
                "packages/sage-common/src/sage/common/utils",
                "tools",
                "examples",
                "scripts",
            ]

        # 获取所有Python文件
        self.all_python_files = self.get_all_python_files()
        orphaned_files = []

        for check_dir in check_directories:
            check_path = self.project_root / check_dir
            if not check_path.exists():
                continue

            for py_file in check_path.rglob("*.py"):
                if py_file.name in self.exclude_patterns:
                    continue

                # 检查是否被引用
                references = self.check_file_references(py_file, self.all_python_files)

                if not references:
                    stat = py_file.stat()
                    orphaned_files.append(
                        OrphanedFile(
                            path=py_file,
                            relative_path=py_file.relative_to(self.project_root),
                            module_path=self.extract_module_path(py_file),
                            size_bytes=stat.st_size,
                            last_modified=stat.st_mtime,
                        )
                    )

        return orphaned_files

    def get_file_analysis(self, file_path: Path) -> dict:
        """获取文件的详细分析信息"""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            lines = content.count("\n") + 1
            functions = len(re.findall(r"^\s*def\s+", content, re.MULTILINE))
            classes = len(re.findall(r"^\s*class\s+", content, re.MULTILINE))
            imports = len(re.findall(r"^\s*(import|from)\s+", content, re.MULTILINE))

            return {
                "lines": lines,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "has_main": "__main__" in content,
                "has_docstring": content.strip().startswith('"""')
                or content.strip().startswith("'''"),
            }
        except Exception:
            return {}


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小（使用统一的格式化函数）"""
    return format_size_compact(size_bytes)


def analyze_orphaned_files(
    project_root: Path, verbose: bool = False
) -> tuple[list[OrphanedFile], dict]:
    """分析项目中的废弃文件"""
    detector = OrphanedFileDetector(project_root)
    orphaned_files = detector.detect_orphaned_files()

    # 统计信息
    total_size = sum(f.size_bytes for f in orphaned_files)
    categories = {}

    for file in orphaned_files:
        category = str(file.relative_path).split("/")[0]
        if category not in categories:
            categories[category] = {"count": 0, "size": 0}
        categories[category]["count"] += 1
        categories[category]["size"] += file.size_bytes

    stats = {
        "total_files": len(orphaned_files),
        "total_size": total_size,
        "categories": categories,
    }

    return orphaned_files, stats
