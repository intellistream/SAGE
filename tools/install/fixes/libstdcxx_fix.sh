#!/bin/bash
# libstdc++ 版本兼容性检查与自动升级
# 目标: 确保提供 GLIBCXX_3.4.30 (sage_flow C++ 扩展所需)

source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 检测当前 (conda) Python 对应的 libstdc++.so.6 是否包含指定符号
_detect_libstdcxx_symbol() {
    local symbol="$1"
    local python_cmd="${PYTHON_CMD:-python3}"
    local lib_path=""

    lib_path=$($python_cmd - <<'PY'
import os, sys, glob
exe = sys.executable
search = [
    os.path.join(os.path.dirname(exe), '..', 'lib', 'libstdc++.so.6'),
    os.path.join(os.path.dirname(exe), 'libstdc++.so.6'),
]
for p in search:
    p = os.path.abspath(p)
    if os.path.exists(p):
        print(p)
        break
PY
    )

    if [ -z "$lib_path" ] || [ ! -f "$lib_path" ]; then
        echo ""  # 未找到
        return 2
    fi

    if strings "$lib_path" 2>/dev/null | grep -q "$symbol"; then
        echo "$lib_path"
        return 0
    else
        echo "$lib_path"
        return 1
    fi
}

ensure_libstdcxx_compatibility() {
    local required_symbol="GLIBCXX_3.4.30"
    local log_file="${1:-install.log}"

    echo -e "${BLUE}🔧 检查 libstdc++ 符号 ${required_symbol} ...${NC}"
    echo "$(date): 开始检查 libstdc++ (${required_symbol})" >> "$log_file"

    # 仅在 conda 环境或显式使用 conda 安装模式时尝试处理
    if ! command -v conda >/dev/null 2>&1; then
        echo -e "${DIM}未检测到 conda，跳过 libstdc++ 自动升级${NC}"
        echo "$(date): 跳过 libstdc++ 检查（无 conda）" >> "$log_file"
        return 0
    fi

    local lib_path
    lib_path=$(_detect_libstdcxx_symbol "$required_symbol")
    local detect_status=$?

    if [ $detect_status -eq 0 ]; then
        echo -e "${CHECK} 已满足: $required_symbol (lib: $lib_path)"
        echo "$(date): libstdc++ 已满足 ($lib_path)" >> "$log_file"
        return 0
    fi

    if [ $detect_status -eq 2 ]; then
        echo -e "${WARNING} 未找到与 Python 绑定的 libstdc++.so.6，尝试继续${NC}"
        echo "$(date): 未找到 libstdc++.so.6" >> "$log_file"
    else
        echo -e "${WARNING} 当前 libstdc++ ($lib_path) 缺少 $required_symbol，尝试升级...${NC}"
        echo "$(date): 缺少符号，准备升级 ($lib_path)" >> "$log_file"
    fi

    # 选择安装工具
    local solver_cmd=""
    if command -v mamba >/dev/null 2>&1; then
        solver_cmd="mamba install -y -c conda-forge libstdcxx-ng>=13"
    else
        solver_cmd="conda install -y -c conda-forge libstdcxx-ng>=13"
    fi

    echo -e "${DIM}执行: $solver_cmd${NC}"
    echo "$(date): 执行 $solver_cmd" >> "$log_file"
    if $solver_cmd >>"$log_file" 2>&1; then
        echo -e "${CHECK} libstdc++ 升级完成，重新验证..."
        lib_path=$(_detect_libstdcxx_symbol "$required_symbol")
        detect_status=$?
        if [ $detect_status -eq 0 ]; then
            echo -e "${CHECK} 升级后已检测到符号 $required_symbol"
            echo "$(date): 升级成功并验证通过" >> "$log_file"
            return 0
        else
            echo -e "${CROSS} 升级后仍未检测到 $required_symbol，请考虑在目标环境重新编译扩展${NC}"
            echo "$(date): 升级后仍缺少符号" >> "$log_file"
            return 1
        fi
    else
        echo -e "${CROSS} libstdc++ 升级失败，详见日志 ${log_file}${NC}"
        echo "$(date): 升级命令执行失败" >> "$log_file"
        return 1
    fi
}

export -f ensure_libstdcxx_compatibility