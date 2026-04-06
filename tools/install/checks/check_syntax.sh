#!/bin/bash
# SAGE 安装脚本语法检查工具


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

echo "🔍 检查所有模块的语法..."

# 检查主脚本
echo "检查主脚本..."
if bash -n quickstart.sh; then
    echo "✅ quickstart.sh 语法正确"
else
    echo "❌ quickstart.sh 语法错误"
    exit 1
fi

# 检查所有模块
for dir in ui checks installers fixes cleanup conda lib tests; do
    echo "检查 $dir 模块..."
    for file in tools/install/$dir/*.sh; do
        if [ -f "$file" ]; then
            if bash -n "$file"; then
                echo "  ✅ $(basename "$file") 语法正确"
            else
                echo "  ❌ $(basename "$file") 语法错误"
                exit 1
            fi
        fi
    done
done

echo ""
echo "🎉 所有模块语法检查通过！"
