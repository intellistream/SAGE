#!/bin/bash
# SAGE 全局 unbound variable 修复脚本
# 自动在所有安装脚本开头添加安全的环境变量默认值

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo -e "${BLUE}🔧 SAGE unbound variable 全局修复工具${NC}"
echo ""

# 需要添加的安全默认值
SAFE_DEFAULTS='
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
CONDA_PREFIX="${CONDA_PREFIX:-}"
WSL_DISTRO_NAME="${WSL_DISTRO_NAME:-}"
SAGE_AUTO_CONFIRM="${SAGE_AUTO_CONFIRM:-}"
SAGE_INSTALL_LOG="${SAGE_INSTALL_LOG:-}"
SAGE_ENV_NAME="${SAGE_ENV_NAME:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
PYTHON_CMD="${PYTHON_CMD:-}"
PIP_CMD="${PIP_CMD:-}"
LANG="${LANG:-}"
LC_ALL="${LC_ALL:-}"
LC_CTYPE="${LC_CTYPE:-}"
HOME="${HOME:-$(/usr/bin/env | grep ^HOME= | cut -d= -f2 || echo /root)}"

'

# 查找所有需要修复的脚本文件
find_scripts_to_fix() {
    find "$REPO_ROOT/tools/install" -name "*.sh" -type f \
        ! -path "*/test*" \
        ! -path "*/.git/*" \
        ! -name "fix_unbound_variables.sh"
}

# 检查文件是否已经有安全默认值
has_safe_defaults() {
    local file="$1"
    grep -q "环境变量安全默认值" "$file" 2>/dev/null
}

# 为文件添加安全默认值
add_safe_defaults() {
    local file="$1"
    local temp_file="${file}.tmp"

    # 读取文件内容
    local shebang=""
    local after_shebang=""
    local found_shebang=false

    # 提取 shebang 和后续内容
    while IFS= read -r line; do
        if [ "$found_shebang" = false ] && [[ "$line" =~ ^#! ]]; then
            shebang="$line"
            found_shebang=true
        elif [ "$found_shebang" = true ] && [ -z "$after_shebang" ]; then
            # 跳过空行和注释直到找到第一行实际代码
            if [[ "$line" =~ ^[[:space:]]*$ ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
                after_shebang+="$line"$'\n'
            else
                # 找到第一行实际代码，插入安全默认值
                {
                    echo "$shebang"
                    echo "$after_shebang"
                    echo "$SAFE_DEFAULTS"
                    echo "$line"
                    cat
                } > "$temp_file"
                break
            fi
        fi
    done < "$file"

    # 如果成功创建了临时文件，替换原文件
    if [ -f "$temp_file" ]; then
        mv "$temp_file" "$file"
        chmod +x "$file"
        return 0
    fi

    return 1
}

# 直接在 source 行之后添加安全默认值（更简单的方法）
add_safe_defaults_simple() {
    local file="$1"
    local temp_file="${file}.tmp"

    # 使用 awk 处理，在第一个非 source 行之前插入安全默认值
    awk -v defaults="$SAFE_DEFAULTS" '
        BEGIN { inserted = 0 }
        /^[[:space:]]*source / {
            print
            source_found = 1
            next
        }
        source_found && !inserted && !/^[[:space:]]*source / {
            print defaults
            inserted = 1
        }
        { print }
        END {
            if (!inserted && source_found) {
                print defaults
            }
        }
    ' "$file" > "$temp_file"

    # 如果没有 source 语句，在 shebang 后面第一个非空非注释行前插入
    if ! grep -q "环境变量安全默认值" "$temp_file" 2>/dev/null; then
        awk -v defaults="$SAFE_DEFAULTS" '
            BEGIN { inserted = 0; after_shebang = 0 }
            /^#!/ && NR == 1 {
                print
                after_shebang = 1
                next
            }
            after_shebang && !inserted && !/^[[:space:]]*#/ && !/^[[:space:]]*$/ {
                print defaults
                inserted = 1
            }
            { print }
        ' "$file" > "$temp_file"
    fi

    if [ -f "$temp_file" ]; then
        mv "$temp_file" "$file"
        chmod +x "$file"
        return 0
    fi

    return 1
}

# 主修复逻辑
echo -e "${YELLOW}正在扫描需要修复的脚本...${NC}"
scripts=$(find_scripts_to_fix)
total=$(echo "$scripts" | wc -l)
fixed=0
skipped=0

echo -e "${BLUE}找到 $total 个脚本文件${NC}"
echo ""

for script in $scripts; do
    relative_path="${script#$REPO_ROOT/}"

    if has_safe_defaults "$script"; then
        echo -e "${GREEN}✓${NC} 已修复: $relative_path"
        ((skipped++))
    else
        echo -e "${YELLOW}🔧${NC} 修复中: $relative_path"
        if add_safe_defaults_simple "$script"; then
            echo -e "${GREEN}✓${NC} 修复完成: $relative_path"
            ((fixed++))
        else
            echo -e "${RED}✗${NC} 修复失败: $relative_path"
        fi
    fi
done

echo ""
echo -e "${GREEN}${BOLD}修复完成！${NC}"
echo -e "  总计: $total 个文件"
echo -e "  新修复: ${GREEN}$fixed${NC} 个"
echo -e "  已修复: ${BLUE}$skipped${NC} 个"
echo ""
echo -e "${YELLOW}提示：${NC}如果还有问题，请运行："
echo -e "  ${BLUE}./tools/install/fixes/fix_unbound_variables.sh${NC}"
