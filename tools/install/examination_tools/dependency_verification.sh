#!/bin/bash
# SAGE 依赖验证模块
# 功能：验证下载包的 checksum、检查安全漏洞（safety/pip-audit）

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# ============================================================================
# Checksum 验证
# ============================================================================

# 计算文件 SHA256 checksum
compute_file_checksum() {
    local file_path="$1"

    if [ ! -f "$file_path" ]; then
        echo -e "${CROSS} 文件不存在: $file_path"
        return 1
    fi

    if command -v sha256sum &> /dev/null; then
        sha256sum "$file_path" | awk '{print $1}'
    elif command -v shasum &> /dev/null; then
        shasum -a 256 "$file_path" | awk '{print $1}'
    else
        echo -e "${CROSS} 无法找到 SHA256 工具 (sha256sum 或 shasum)"
        return 1
    fi
}

# 从 PyPI JSON API 获取包的 checksum
get_pypi_package_checksums() {
    local package_name="$1"
    local package_version="$2"

    if [ -z "$package_name" ]; then
        echo -e "${CROSS} 包名不能为空"
        return 1
    fi

    # 构造 PyPI API URL
    local pypi_url="https://pypi.org/pypi/${package_name}/json"

    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        echo -e "${WARNING} 无法获取 PyPI 校验和：未安装 curl 或 wget"
        return 1
    fi

    # 使用 curl 或 wget 获取包信息
    local json_response
    if command -v curl &> /dev/null; then
        json_response=$(curl -s "$pypi_url" 2>/dev/null || true)
    else
        json_response=$(wget -q -O - "$pypi_url" 2>/dev/null || true)
    fi

    if [ -z "$json_response" ]; then
        echo -e "${WARNING} 无法从 PyPI 获取包信息: $package_name"
        return 1
    fi

    # 解析 JSON 获取校验和
    # 如果有 Python，使用 Python 解析；否则使用 grep 和 sed 简单解析
    if command -v python3 &> /dev/null; then
        python3 << PYTHON_EOF
import json
import sys

try:
    data = json.loads('$json_response')
    if 'releases' in data:
        releases = data['releases']
        for version, files in releases.items():
            if '$package_version' == '' or version == '$package_version':
                for file_info in files:
                    if 'digests' in file_info and 'sha256' in file_info['digests']:
                        print(f"{file_info['filename']}:{file_info['digests']['sha256']}")
except:
    pass
PYTHON_EOF
    else
        # 简单的 grep 方式提取校验和
        echo "$json_response" | grep -o '"sha256":"[^"]*"' | grep -o '[a-f0-9]\{64\}'
    fi
}

# 验证下载的包文件 checksum
verify_package_checksum() {
    local package_path="$1"
    local expected_checksum="$2"
    local package_name=$(basename "$package_path")

    if [ ! -f "$package_path" ]; then
        echo -e "${CROSS} 包文件不存在: $package_path"
        return 1
    fi

    echo -e "${INFO} 计算 $package_name 的 SHA256..."
    local actual_checksum=$(compute_file_checksum "$package_path")

    if [ $? -ne 0 ]; then
        return 1
    fi

    if [ "$actual_checksum" = "$expected_checksum" ]; then
        echo -e "${CHECK} ✓ 校验和验证通过"
        return 0
    else
        echo -e "${CROSS} ✗ 校验和不匹配！"
        echo -e "${DIM}  期望: $expected_checksum${NC}"
        echo -e "${DIM}  实际: $actual_checksum${NC}"
        echo -e "${WARNING} ⚠️  包可能已被篡改，请勿继续使用"
        return 1
    fi
}

# ============================================================================
# 安全漏洞检查
# ============================================================================

# 检查是否安装了 safety 或 pip-audit
check_security_tools() {
    local tools_available=()

    # 检查 pip-audit（推荐）
    if pip list 2>/dev/null | grep -q "^pip-audit"; then
        tools_available+=("pip-audit")
    elif python3 -m pip_audit --version &>/dev/null 2>&1; then
        tools_available+=("pip-audit")
    fi

    # 检查 safety
    if pip list 2>/dev/null | grep -q "^safety"; then
        tools_available+=("safety")
    elif python3 -m safety --version &>/dev/null 2>&1; then
        tools_available+=("safety")
    fi

    # 检查 bandit（代码审计）
    if pip list 2>/dev/null | grep -q "^bandit"; then
        tools_available+=("bandit")
    elif command -v bandit &>/dev/null; then
        tools_available+=("bandit")
    fi

    if [ ${#tools_available[@]} -eq 0 ]; then
        return 1
    fi

    # 返回可用工具列表
    echo "${tools_available[@]}"
    return 0
}

# 使用 pip-audit 检查依赖漏洞
check_vulnerabilities_pip_audit() {
    local requirements_file="$1"
    local report_file="${2:-security_audit_pip_audit.json}"

    if [ -z "$requirements_file" ] || [ ! -f "$requirements_file" ]; then
        echo -e "${CROSS} Requirements 文件不存在: $requirements_file"
        return 1
    fi

    echo -e "${INFO} 使用 pip-audit 检查漏洞..."

    # 检查 pip-audit 是否可用
    if ! python3 -m pip_audit --version &>/dev/null 2>&1; then
        echo -e "${WARNING} pip-audit 未安装，尝试安装..."
        pip install --quiet pip-audit 2>/dev/null || {
            echo -e "${CROSS} 无法安装 pip-audit"
            return 1
        }
    fi

    # 运行 pip-audit
    if python3 -m pip_audit --desc -r "$requirements_file" --output "$report_file" 2>/dev/null; then
        echo -e "${CHECK} ✓ 漏洞扫描完成: $report_file"
        return 0
    else
        # 如果返回非零，可能表示发现了漏洞
        echo -e "${WARNING} 发现安全漏洞，详见: $report_file"
        return 1
    fi
}

# 使用 safety 检查依赖漏洞
check_vulnerabilities_safety() {
    local requirements_file="$1"
    local report_file="${2:-security_audit_safety.json}"

    if [ -z "$requirements_file" ] || [ ! -f "$requirements_file" ]; then
        echo -e "${CROSS} Requirements 文件不存在: $requirements_file"
        return 1
    fi

    echo -e "${INFO} 使用 safety 检查漏洞..."

    # 检查 safety 是否可用
    if ! python3 -m safety --version &>/dev/null 2>&1; then
        echo -e "${WARNING} safety 未安装，尝试安装..."
        pip install --quiet safety 2>/dev/null || {
            echo -e "${CROSS} 无法安装 safety"
            return 1
        }
    fi

    # 运行 safety
    if python3 -m safety check -r "$requirements_file" --json > "$report_file" 2>&1; then
        echo -e "${CHECK} ✓ 漏洞扫描完成: $report_file"
        return 0
    else
        # 如果返回非零，可能表示发现了漏洞
        if grep -q "vulnerability" "$report_file" 2>/dev/null; then
            echo -e "${WARNING} 发现安全漏洞，详见: $report_file"
            return 1
        fi
    fi
}

# 检查依赖的安全漏洞（主函数）
check_vulnerabilities() {
    local requirements_file="$1"
    local output_dir="${2:-.}"
    local scan_type="${3:-auto}"  # auto, pip-audit, safety, all

    if [ -z "$requirements_file" ] || [ ! -f "$requirements_file" ]; then
        echo -e "${CROSS} Requirements 文件不存在: $requirements_file"
        return 1
    fi

    echo -e "${BLUE}=== 安全漏洞扫描 ===${NC}"
    echo -e "${INFO} 扫描文件: $requirements_file"

    local has_vulnerabilities=false

    # 检查可用工具
    local available_tools=$(check_security_tools)

    if [ -z "$available_tools" ]; then
        echo -e "${WARNING} ⚠️  未检测到安全扫描工具 (pip-audit/safety)"
        echo -e "${DIM}  建议: pip install pip-audit safety${NC}"
        return 1
    fi

    echo -e "${INFO} 可用工具: $available_tools"

    # 根据扫描类型选择工具
    case "$scan_type" in
        pip-audit)
            check_vulnerabilities_pip_audit "$requirements_file" "$output_dir/security_audit_pip_audit.json" || has_vulnerabilities=true
            ;;
        safety)
            check_vulnerabilities_safety "$requirements_file" "$output_dir/security_audit_safety.json" || has_vulnerabilities=true
            ;;
        all)
            check_vulnerabilities_pip_audit "$requirements_file" "$output_dir/security_audit_pip_audit.json" || has_vulnerabilities=true
            check_vulnerabilities_safety "$requirements_file" "$output_dir/security_audit_safety.json" || has_vulnerabilities=true
            ;;
        auto|*)
            # 优先使用 pip-audit，如果不可用则使用 safety
            if echo "$available_tools" | grep -q "pip-audit"; then
                check_vulnerabilities_pip_audit "$requirements_file" "$output_dir/security_audit_pip_audit.json" || has_vulnerabilities=true
            elif echo "$available_tools" | grep -q "safety"; then
                check_vulnerabilities_safety "$requirements_file" "$output_dir/security_audit_safety.json" || has_vulnerabilities=true
            fi
            ;;
    esac

    if [ "$has_vulnerabilities" = true ]; then
        echo -e "${WARNING} ⚠️  发现安全漏洞，请审查报告"
        return 1
    fi

    echo -e "${CHECK} 安全扫描完成"
    return 0
}

# ============================================================================
# 依赖完整性检查
# ============================================================================

# 验证 pip 安装的包完整性
verify_pip_packages() {
    local requirements_file="$1"

    if [ -z "$requirements_file" ] || [ ! -f "$requirements_file" ]; then
        echo -e "${CROSS} Requirements 文件不存在: $requirements_file"
        return 1
    fi

    echo -e "${INFO} 验证已安装包的完整性..."

    # 使用 pip check 验证依赖
    if ! python3 -m pip check >/dev/null 2>&1; then
        echo -e "${CROSS} 发现依赖冲突"
        python3 -m pip check
        return 1
    fi

    echo -e "${CHECK} ✓ 所有包依赖验证通过"
    return 0
}

# 验证系统中的所有 pip 包
verify_all_installed_packages() {
    echo -e "${INFO} 验证所有已安装的包..."

    if ! python3 -m pip check >/dev/null 2>&1; then
        echo -e "${CROSS} 发现依赖冲突:"
        python3 -m pip check
        return 1
    fi

    echo -e "${CHECK} ✓ 所有包完整性验证通过"
    return 0
}

# ============================================================================
# 深度依赖验证（--verify-deps）
# ============================================================================

# 执行深度验证
perform_deep_verification() {
    local requirements_file="$1"
    local output_dir="${2:-.}"
    local strict="${3:-false}"  # 严格模式：有任何问题则失败

    echo -e "${BLUE}=== 深度依赖验证 (--verify-deps) ===${NC}"
    echo ""

    mkdir -p "$output_dir"

    local all_passed=true

    # 1. 验证 pip 依赖
    echo "1️⃣  验证 pip 包依赖..."
    if [ -f "$requirements_file" ]; then
        verify_pip_packages "$requirements_file" || all_passed=false
    else
        verify_all_installed_packages || all_passed=false
    fi

    echo ""

    # 2. 安全漏洞扫描
    echo "2️⃣  运行安全漏洞扫描..."
    if [ -f "$requirements_file" ]; then
        check_vulnerabilities "$requirements_file" "$output_dir" "all" || {
            if [ "$strict" = "true" ]; then
                all_passed=false
            fi
        }
    fi

    echo ""

    # 3. 检查已安装包版本
    echo "3️⃣  检查包版本兼容性..."
    local incompatible_packages=()

    while IFS= read -r line; do
        # 跳过注释和空行
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # 提取包名
        local package=$(echo "$line" | cut -d'=' -f1 | cut -d'>' -f1 | cut -d'<' -f1 | xargs)

        if ! pip show "$package" &>/dev/null 2>&1; then
            incompatible_packages+=("$package")
        fi
    done < <(cat "$requirements_file" 2>/dev/null || true)

    if [ ${#incompatible_packages[@]} -gt 0 ]; then
        echo -e "${WARNING} 发现未安装的包:"
        printf '  - %s\n' "${incompatible_packages[@]}"
        if [ "$strict" = "true" ]; then
            all_passed=false
        fi
    else
        echo -e "${CHECK} ✓ 所有包都已正确安装"
    fi

    echo ""

    # 最终结果
    if [ "$all_passed" = true ]; then
        echo -e "${CHECK} ✅ 深度验证通过"
        return 0
    else
        echo -e "${WARNING} ⚠️  深度验证发现问题，请查看详细报告"
        return 1
    fi
}

# ============================================================================
# 导出函数给外部调用
# ============================================================================

# 确保脚本被源引用时导出函数
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    # 被源引用
    :
else
    # 直接执行此脚本
    echo -e "${INFO} 依赖验证模块"
    echo "使用方法："
    echo "  source $0"
    echo "  compute_file_checksum <file>"
    echo "  verify_package_checksum <file> <checksum>"
    echo "  check_vulnerabilities <requirements.txt> [output_dir] [scan_type]"
    echo "  perform_deep_verification <requirements.txt> [output_dir] [strict]"
fi
