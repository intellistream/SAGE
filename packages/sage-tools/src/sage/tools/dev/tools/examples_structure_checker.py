"""
Examples 目录结构检查器

确保 examples/ 目录保持正确的结构：
- 只允许 apps/ 和 tutorials/ 两个顶层子目录
- 禁止在顶层创建其他目录（如 kernel/, unlearning/ 等）
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExamplesStructureResult:
    """Examples 结构检查结果"""

    passed: bool
    violations: list[str]
    allowed_dirs: list[str]
    unexpected_dirs: list[str]


class ExamplesStructureChecker:
    """Examples 目录结构检查器"""

    # 允许的顶层目录（除了文件和隐藏目录）
    ALLOWED_TOP_DIRS = {"apps", "tutorials"}

    # 允许的顶层文件
    ALLOWED_TOP_FILES = {"README.md", "requirements.txt", "__init__.py"}

    # 允许的特殊项（符号链接等）
    ALLOWED_SPECIAL = {"data"}  # data 是指向 tutorials/agents/data 的符号链接

    def __init__(self, examples_dir: Path):
        """
        初始化检查器

        Args:
            examples_dir: examples 目录路径
        """
        self.examples_dir = Path(examples_dir)

    def check_structure(self) -> ExamplesStructureResult:
        """
        检查 examples 目录结构

        Returns:
            检查结果
        """
        violations = []
        unexpected_dirs = []

        if not self.examples_dir.exists():
            return ExamplesStructureResult(
                passed=False,
                violations=["examples/ 目录不存在"],
                allowed_dirs=[],
                unexpected_dirs=[],
            )

        # 检查顶层目录
        for item in self.examples_dir.iterdir():
            # 跳过隐藏文件/目录和 __pycache__
            if item.name.startswith(".") or item.name == "__pycache__":
                continue

            # 先检查符号链接（因为符号链接也可能 is_dir() 返回 True）
            if item.is_symlink():
                if item.name not in self.ALLOWED_SPECIAL:
                    violations.append(f"在 examples/ 下发现不期望的符号链接: {item.name}")
            # 检查是否是目录
            elif item.is_dir():
                if item.name not in self.ALLOWED_TOP_DIRS:
                    unexpected_dirs.append(item.name)
                    violations.append(
                        f"在 examples/ 下发现不允许的目录: {item.name}\n"
                        f"  应该移动到 examples/tutorials/{item.name}/"
                    )
            # 检查是否是文件
            elif item.is_file():
                if item.name not in self.ALLOWED_TOP_FILES:
                    violations.append(f"在 examples/ 下发现不期望的文件: {item.name}")

        # 验证必需的目录存在
        for required_dir in self.ALLOWED_TOP_DIRS:
            dir_path = self.examples_dir / required_dir
            if not dir_path.exists():
                violations.append(f"缺少必需的目录: examples/{required_dir}/")

        passed = len(violations) == 0

        return ExamplesStructureResult(
            passed=passed,
            violations=violations,
            allowed_dirs=list(self.ALLOWED_TOP_DIRS),
            unexpected_dirs=unexpected_dirs,
        )

    def get_structure_guide(self) -> str:
        """
        获取结构规范说明

        Returns:
            结构规范的文本说明
        """
        return """
Examples 目录结构规范:

examples/
├── apps/           # 应用示例（完整的应用程序）
├── tutorials/      # 教程示例（各类功能演示）
│   ├── agents/
│   ├── core-api/
│   ├── kernel/
│   ├── memory/
│   ├── multimodal/
│   ├── rag/
│   ├── scheduler/
│   ├── service/
│   ├── unlearning/
│   └── ...
├── README.md
└── requirements.txt

规则:
1. 顶层只允许 'apps' 和 'tutorials' 两个目录
2. 所有新的示例类别应放在 tutorials/ 下作为子目录
3. 不允许在 examples/ 顶层创建其他目录（如 kernel/, unlearning/ 等）
"""


def check_examples_structure(project_root: Path) -> ExamplesStructureResult:
    """
    便捷函数：检查 examples 目录结构

    Args:
        project_root: 项目根目录

    Returns:
        检查结果
    """
    checker = ExamplesStructureChecker(project_root)
    return checker.check_structure()
