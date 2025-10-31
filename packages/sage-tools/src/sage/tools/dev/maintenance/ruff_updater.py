"""
Ruff ignore 规则更新工具

批量更新所有 pyproject.toml 文件中的 ruff.lint.ignore 规则

从 tools/maintenance/helpers/update_ruff_ignore.py 迁移

Author: SAGE Team
Date: 2025-10-27
"""

import re
from pathlib import Path

# 默认的包 pyproject.toml 文件列表
DEFAULT_PACKAGE_FILES = [
    "packages/sage-benchmark/pyproject.toml",
    "packages/sage-common/pyproject.toml",
    "packages/sage-kernel/pyproject.toml",
    "packages/sage-middleware/pyproject.toml",
    "packages/sage-tools/pyproject.toml",
    "packages/sage-libs/pyproject.toml",
    "packages/sage/pyproject.toml",
    "packages/sage-studio/pyproject.toml",
    "packages/sage-apps/pyproject.toml",
    "packages/sage-platform/pyproject.toml",
]


class RuffIgnoreUpdater:
    """Ruff ignore 规则更新器"""

    def __init__(self, root_dir: Path | None = None):
        """
        初始化更新器

        Args:
            root_dir: 项目根目录，默认为当前目录
        """
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()

    def update_file(
        self,
        file_path: Path,
        rules_to_add: list[str],
        descriptions: dict[str, str] | None = None,
    ) -> bool:
        """
        更新单个 pyproject.toml 文件

        Args:
            file_path: 文件路径
            rules_to_add: 要添加的规则列表，如 ["B904", "C901"]
            descriptions: 规则描述字典，如 {"B904": "raise-without-from"}

        Returns:
            是否有更新
        """
        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            return False

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️  读取文件失败: {file_path} - {e}")
            return False

        # 检查是否已经有所有规则
        all_present = all(f'"{rule}"' in content for rule in rules_to_add)
        if all_present:
            print(f"✅ {file_path.name} 已包含所有规则")
            return False

        # 查找 [tool.ruff.lint] 下的 ignore 部分
        # 匹配模式: ignore = [ ... ]
        pattern = r"(ignore\s*=\s*\[)(.*?)(\])"

        def replace_ignore(match):
            prefix = match.group(1)
            existing = match.group(2)
            suffix = match.group(3)

            # 解析现有的 ignore 列表
            lines = existing.split("\n")

            # 检查哪些规则需要添加
            rules_to_insert = []
            for rule in rules_to_add:
                if not any(f'"{rule}"' in line or f"'{rule}'" in line for line in lines):
                    rules_to_insert.append(rule)

            if not rules_to_insert:
                return match.group(0)

            # 找到最后一个有效条目
            result_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    result_lines.append(line)

            # 如果 ignore 列表为空或只有注释
            if not result_lines:
                # 添加新条目
                new_entries = []
                for rule in rules_to_insert:
                    desc = descriptions.get(rule, "") if descriptions else ""
                    comment = f"  # {desc}" if desc else ""
                    new_entries.append(f'    "{rule}",{comment}')
                new_content = "\n" + "\n".join(new_entries) + "\n"
                return f"{prefix}{new_content}{suffix}"

            # 在最后一个条目后添加
            new_lines = lines.copy()

            # 找到插入位置（最后一个非空非注释行之后）
            insert_idx = len(new_lines)
            for i in range(len(new_lines) - 1, -1, -1):
                stripped = new_lines[i].strip()
                if stripped and not stripped.startswith("#"):
                    insert_idx = i + 1
                    # 确保最后一项有逗号
                    if not new_lines[i].rstrip().endswith(","):
                        new_lines[i] = new_lines[i].rstrip() + ","
                    break

            # 添加新规则
            for rule in rules_to_insert:
                desc = descriptions.get(rule, "") if descriptions else ""
                comment = f"  # {desc}" if desc else ""
                new_lines.insert(insert_idx, f'    "{rule}",{comment}')
                insert_idx += 1

            new_content = "\n".join(new_lines)
            return f"{prefix}{new_content}{suffix}"

        # 执行替换
        new_content = re.sub(pattern, replace_ignore, content, flags=re.DOTALL)

        if new_content != content:
            try:
                file_path.write_text(new_content, encoding="utf-8")
                print(f"✅ 更新: {file_path}")
                return True
            except Exception as e:
                print(f"⚠️  写入文件失败: {file_path} - {e}")
                return False
        else:
            print(f"ℹ️  无变化: {file_path}")
            return False

    def update_all(
        self,
        rules_to_add: list[str],
        descriptions: dict[str, str] | None = None,
        file_list: list[str] | None = None,
    ) -> dict[str, int]:
        """
        批量更新 pyproject.toml 文件

        Args:
            rules_to_add: 要添加的规则列表
            descriptions: 规则描述字典
            file_list: 要更新的文件列表，默认使用 DEFAULT_PACKAGE_FILES

        Returns:
            更新统计字典
        """
        if file_list is None:
            file_list = DEFAULT_PACKAGE_FILES

        print("🔄 开始批量更新 pyproject.toml 文件...")
        print(f"📝 规则: {', '.join(rules_to_add)}\n")

        stats = {"updated": 0, "skipped": 0, "failed": 0}

        for file_path_str in file_list:
            full_path = self.root_dir / file_path_str
            if self.update_file(full_path, rules_to_add, descriptions):
                stats["updated"] += 1
            else:
                if full_path.exists():
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1

        print("\n✨ 完成！")
        print(f"  ✅ 更新: {stats['updated']}")
        print(f"  ⏭️  跳过: {stats['skipped']}")
        print(f"  ❌ 失败: {stats['failed']}")

        return stats

    def add_b904_c901(self) -> dict[str, int]:
        """
        添加 B904 和 C901 规则（常用快捷方法）

        Returns:
            更新统计字典
        """
        rules = ["B904", "C901"]
        descriptions = {
            "B904": "raise-without-from-inside-except",
            "C901": "complex-structure",
        }
        return self.update_all(rules, descriptions)
