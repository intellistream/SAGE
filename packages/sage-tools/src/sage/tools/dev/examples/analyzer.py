"""
Example Analyzer Module

This module provides tools for analyzing Python example files,
extracting metadata, dependencies, and categorization information.
"""

import ast
import re
from pathlib import Path

from rich.console import Console

from .models import ExampleInfo
from .utils import find_examples_directory, find_project_root

console = Console()


class ExampleAnalyzer:
    """示例代码分析器"""

    def __init__(self):
        """初始化 ExampleAnalyzer

        Raises:
            RuntimeError: 如果找不到 examples 目录（开发环境不可用）
        """
        # 使用新的环境检测工具
        examples_dir = find_examples_directory()
        if examples_dir is None:
            raise RuntimeError(
                "Cannot find SAGE examples directory. "
                "This tool requires a development environment. "
                "Please see the Examples Testing README for setup instructions."
            )

        self.examples_root = examples_dir

        # 同时获取项目根目录
        self.project_root = find_project_root()
        if self.project_root is None:
            # 如果找到了 examples 但找不到项目根，使用 examples 的父目录
            self.project_root = self.examples_root.parent

    def analyze_file(self, file_path: Path) -> ExampleInfo | None:
        """分析单个示例文件

        Args:
            file_path: 示例文件的路径

        Returns:
            ExampleInfo 对象，如果分析失败返回 None
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # 提取导入信息
            imports = self._extract_imports(tree)

            # 检查是否有主函数
            has_main = self._has_main_function(tree)

            # 检查配置和数据依赖
            requires_config = self._requires_config(content)
            requires_data = self._requires_data(content)

            # 估算运行时间
            estimated_runtime = self._estimate_runtime(content)

            # 提取依赖
            dependencies = self._extract_dependencies(imports)

            # 提取测试标记（包括 TEST_TAGS 变量）
            test_tags = self._extract_test_tags(content, tree)

            category = self._get_category(file_path)

            return ExampleInfo(
                file_path=str(file_path),
                category=category,
                imports=imports,
                has_main=has_main,
                requires_config=requires_config,
                requires_data=requires_data,
                estimated_runtime=estimated_runtime,
                dependencies=dependencies,
                test_tags=test_tags,
            )

        except Exception as e:
            console.print(f"[red]分析文件失败 {file_path}: {e}[/red]")
            return None

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        """提取导入语句"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def _has_main_function(self, tree: ast.AST) -> bool:
        """检查是否有主函数"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                return True
            if isinstance(node, ast.If) and hasattr(node.test, "left"):
                if (
                    hasattr(node.test.left, "id")
                    and node.test.left.id == "__name__"
                    and hasattr(node.test.comparators[0], "s")
                    and node.test.comparators[0].s == "__main__"
                ):
                    return True
        return False

    def _requires_config(self, content: str) -> bool:
        """检查是否需要配置文件"""
        config_indicators = [
            ".yaml",
            ".yml",
            ".json",
            ".toml",
            "config",
            "Config",
            "load_dotenv",
            "os.environ",
            "getenv",
        ]
        return any(indicator in content for indicator in config_indicators)

    def _requires_data(self, content: str) -> bool:
        """检查是否需要数据文件"""
        data_indicators = [
            ".csv",
            ".txt",
            ".pdf",
            ".docx",
            "data/",
            "dataset",
            "corpus",
        ]
        return any(indicator in content for indicator in data_indicators)

    def _estimate_runtime(self, content: str) -> str:
        """估算运行时间"""
        # 检查是否有明显的长时间运行指标
        if any(
            keyword in content for keyword in ["time.sleep", "train", "fit", "epochs", "while True"]
        ):
            return "slow"
        # 检查是否是简单的教程示例（优先级高）
        elif any(
            keyword in content for keyword in ["Hello, World!", "HelloBatch", "simple", "basic"]
        ):
            return "quick"
        # 检查网络请求等中等时间指标
        elif any(keyword in content for keyword in ["requests.", "http.", "download", "ray.init"]):
            return "medium"
        # 文件大小作为参考
        elif len(content) < 3000:  # 小于3KB的文件通常是快速示例
            return "quick"
        else:
            return "medium"

    def _extract_dependencies(self, imports: list[str]) -> list[str]:
        """提取外部依赖"""
        external_deps = []

        dependency_map = {
            "openai": "openai",
            "transformers": "transformers",
            "torch": "torch",
            "numpy": "numpy",
            "pandas": "pandas",
            "requests": "requests",
            "yaml": "pyyaml",
            "dotenv": "python-dotenv",
            "chromadb": "chromadb",
            "pymilvus": "pymilvus",
            "redis": "redis",
            "kafka": "kafka-python",
            "cv2": "opencv-python",
        }

        for imp in imports:
            root_module = imp.split(".")[0]
            if root_module in dependency_map:
                external_deps.append(dependency_map[root_module])

        return list(set(external_deps))

    def _extract_test_tags(self, content: str, tree: ast.AST | None = None) -> list[str]:
        """从文件内容中提取测试标记

        支持的标记格式:
        1. Python 变量: TEST_TAGS = ["timeout=120", "slow"]
        2. 注释标记: # @test:skip - 跳过测试
        3. 注释标记: # @test:slow - 标记为慢速测试
        4. 注释标记: # @test:require-api - 需要API密钥
        5. 注释标记: # @test:timeout=120 - 自定义超时时间
        6. 注释标记: @test_skip_ci: true - CI环境中跳过
        """
        tags = []

        # Method 1: Extract from TEST_TAGS variable (highest priority)
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "TEST_TAGS":
                            # Found TEST_TAGS assignment
                            if isinstance(node.value, ast.List):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Constant):
                                        tags.append(str(elt.value))
                                    elif isinstance(elt, ast.Str):  # Python 3.7 compatibility
                                        tags.append(elt.s)

        # Method 2: Extract from comments (Pattern 1: @test:tag or @test:tag=value)
        pattern1 = r"(?:#\s*)?@test:([\w-]+)(?:=([\w-]+))?"
        matches1 = re.findall(pattern1, content, re.IGNORECASE)

        for match in matches1:
            if len(match) == 2 and match[1]:
                # 带值的标记，如 timeout=120
                tags.append(f"{match[0]}={match[1]}")
            else:
                # 简单标记，如 skip
                tags.append(match[0])

        # Method 3: Extract from comments (Pattern 2: @test_tag: value)
        pattern2 = r"@test_([\w-]+):\s*([\w\[\],\s-]+)"
        matches2 = re.findall(pattern2, content, re.IGNORECASE)

        for match in matches2:
            tag_name = match[0]
            tag_value = match[1].strip()
            # 简化标记名（移除值为true的情况，直接使用标记名）
            if tag_value.lower() == "true":
                tags.append(tag_name)
            elif tag_value.lower() == "false":
                # false值不添加标记
                continue
            else:
                # 其他值保留为 tag=value 格式
                tags.append(f"{tag_name}={tag_value}")

        return list(set(tags))

    def _get_category(self, file_path: Path) -> str:
        """获取示例类别

        对于 examples/tutorials/rag/simple_rag.py 这样的文件，
        返回 'rag' 而不是 'tutorials'，以便更细粒度的分类。
        对于 examples/apps/run_app.py 这样的文件，返回 'apps'。
        """
        relative_path = file_path.relative_to(self.examples_root)
        if not relative_path.parts:
            return "unknown"

        # 如果第一级目录是 tutorials，并且有第二级目录，使用第二级
        if len(relative_path.parts) >= 3 and relative_path.parts[0] == "tutorials":
            return str(relative_path.parts[1])

        # 否则使用第一级目录
        return str(relative_path.parts[0])

    def discover_examples(self) -> list[ExampleInfo]:
        """发现所有示例文件"""
        examples = []

        for py_file in self.examples_root.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            example_info = self.analyze_file(py_file)
            if example_info:
                examples.append(example_info)

        return examples
