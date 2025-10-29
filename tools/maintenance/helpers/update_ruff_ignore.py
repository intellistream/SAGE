#!/usr/bin/env python3
"""
批量更新所有 pyproject.toml 文件，在 ruff.lint.ignore 中添加规则

⚠️ 此脚本已迁移到 sage-tools 包
📝 新位置: packages/sage-tools/src/sage/tools/dev/maintenance/ruff_updater.py
🚀 新用法: sage-dev maintenance update-ruff-ignore

保留此文件以便向后兼容
"""

import re
import sys
import warnings
from pathlib import Path

warnings.warn(
    "此脚本已迁移到 sage-tools 包。"
    "请使用: sage-dev maintenance update-ruff-ignore --preset b904-c901",
    DeprecationWarning,
    stacklevel=2,
)

print("=" * 80)
print("⚠️  此脚本已迁移到 sage-tools 包")
print("=" * 80)
print()
print("新的使用方式:")
print("  sage-dev maintenance update-ruff-ignore --preset b904-c901")
print("  sage-dev maintenance update-ruff-ignore --rules B904,C901")
print()
print("或使用 Python API:")
print("  from sage.tools.dev.maintenance import RuffIgnoreUpdater")
print("  updater = RuffIgnoreUpdater(root_dir)")
print("  updater.add_b904_c901()")
print()
print("继续使用旧脚本...")
print()

# 尝试导入新模块
try:
    from sage.tools.dev.maintenance import RuffIgnoreUpdater

    root = Path.cwd()
    updater = RuffIgnoreUpdater(root)
    updater.add_b904_c901()
    sys.exit(0)
except ImportError:
    print("❌ 无法导入新模块，请安装 sage-tools:")
    print("  pip install -e packages/sage-tools")
    sys.exit(1)

# 原始代码保留（以防万一）
# 主包的 pyproject.toml 文件
PACKAGE_TOML_FILES = [
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


def update_pyproject_toml(file_path: Path):
    """更新单个 pyproject.toml 文件"""
    if not file_path.exists():
        print(f"⚠️  文件不存在: {file_path}")
        return False

    content = file_path.read_text()

    # 检查是否已经有 B904 或 C901
    if '"B904"' in content and '"C901"' in content:
        print(f"✅ {file_path.name} 已包含 B904 和 C901")
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

        # 检查是否已有 B904 或 C901
        has_b904 = any('"B904"' in line or "'B904'" in line for line in lines)
        has_c901 = any('"C901"' in line or "'C901'" in line for line in lines)

        # 如果都有，不需要修改
        if has_b904 and has_c901:
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
            new_content = '\n    "B904",  # raise-without-from-inside-except\n    "C901",  # complex-structure\n'
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
        if not has_b904:
            new_lines.insert(insert_idx, '    "B904",  # raise-without-from-inside-except')
            insert_idx += 1
        if not has_c901:
            new_lines.insert(insert_idx, '    "C901",  # complex-structure')

        new_content = "\n".join(new_lines)
        return f"{prefix}{new_content}{suffix}"

    # 执行替换
    new_content = re.sub(pattern, replace_ignore, content, flags=re.DOTALL)

    if new_content != content:
        file_path.write_text(new_content)
        print(f"✅ 更新: {file_path}")
        return True
    else:
        print(f"ℹ️  无变化: {file_path}")
        return False


def main():
    """主函数"""
    root = Path(__file__).parent
    updated = 0

    print("🔄 开始批量更新 pyproject.toml 文件...\n")

    for file_path in PACKAGE_TOML_FILES:
        full_path = root / file_path
        if update_pyproject_toml(full_path):
            updated += 1

    print(f"\n✨ 完成！更新了 {updated} 个文件")


if __name__ == "__main__":
    main()
