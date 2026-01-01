#!/bin/bash
# SAGE 全局 unbound variable 修复脚本 v2
# 使用更简单的 Python 脚本方式

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "🔧 SAGE unbound variable 全局修复工具 v2"
echo ""

# 使用 Python 脚本进行修复
python3 << 'PYTHON_SCRIPT'
import os
import re
from pathlib import Path

SAFE_DEFAULTS = '''
# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

'''

def find_install_scripts():
    """查找所有安装脚本"""
    scripts = []
    tools_dir = Path("tools/install")

    for sh_file in tools_dir.rglob("*.sh"):
        # 跳过修复脚本自身
        if "fix_unbound_variables" in str(sh_file):
            continue
        scripts.append(sh_file)

    return sorted(scripts)

def already_has_safe_defaults(content):
    """检查是否已经有安全默认值"""
    return "环境变量安全默认值" in content

def insert_safe_defaults(file_path):
    """在文件中插入安全默认值"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 如果已经有了，跳过
        content = ''.join(lines)
        if already_has_safe_defaults(content):
            return False, "已存在安全默认值"

        # 找到插入位置：shebang 后面第一个实际代码行之前
        insert_pos = 1  # 默认在第二行（shebang 后）

        for i, line in enumerate(lines[1:], start=1):
            # 跳过空行和注释
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # 跳过 source 语句
            if stripped.startswith('source ') or stripped.startswith('. '):
                continue

            # 找到第一个实际代码行
            insert_pos = i
            break

        # 插入安全默认值
        lines.insert(insert_pos, SAFE_DEFAULTS)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True, "修复成功"

    except Exception as e:
        return False, f"错误: {str(e)}"

def main():
    print("正在扫描需要修复的脚本...")
    scripts = find_install_scripts()
    print(f"找到 {len(scripts)} 个脚本文件\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for script in scripts:
        modified, message = insert_safe_defaults(script)

        if modified:
            print(f"✓ 修复完成: {script}")
            success_count += 1
        elif "已存在" in message:
            print(f"○ 跳过: {script} ({message})")
            skip_count += 1
        else:
            print(f"✗ 失败: {script} ({message})")
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"修复统计:")
    print(f"  成功: {success_count} 个")
    print(f"  跳过: {skip_count} 个")
    print(f"  失败: {fail_count} 个")
    print(f"{'='*60}")

    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    exit(main())

PYTHON_SCRIPT
