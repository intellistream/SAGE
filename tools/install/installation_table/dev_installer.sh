#!/bin/bash
# SAGE 安装脚本 - 开发工具包安装器
# 负责安装开发工具相关的依赖包

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 导入核心安装器函数
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"

# 安装C++扩展函数
install_cpp_extensions() {
    local log_file="$1"
    
    echo -e "${DIM}正在检查系统构建工具...${NC}"
    echo "$(date): 开始安装C++扩展" >> "$log_file"
    
    # 检查必要的构建工具
    local missing_tools=()
    
    if ! command -v gcc >/dev/null 2>&1 && ! command -v g++ >/dev/null 2>&1; then
        missing_tools+=("gcc/g++")
    fi
    
    if ! command -v cmake >/dev/null 2>&1; then
        missing_tools+=("cmake")
    fi
    
    if ! command -v make >/dev/null 2>&1; then
        missing_tools+=("make")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo -e "${WARNING} 缺少构建工具: ${missing_tools[*]}"
        echo -e "${DIM}Ubuntu/Debian: sudo apt install build-essential cmake${NC}"
        echo -e "${DIM}CentOS/RHEL: sudo yum groupinstall 'Development Tools' && sudo yum install cmake${NC}"
        echo -e "${DIM}macOS: xcode-select --install && brew install cmake${NC}"
        echo "$(date): 构建工具检查失败: ${missing_tools[*]}" >> "$log_file"
        return 1
    fi
    
    echo -e "${CHECK} 构建工具检查完成"
    echo ""
    
    # 尝试使用 sage 命令安装扩展
    echo -e "${DIM}正在安装C++扩展...${NC}"
    
    if command -v sage >/dev/null 2>&1; then
        SAGE_CMD="sage"
    elif python3 -c "import sage.tools.cli.main" 2>/dev/null; then
        SAGE_CMD="python3 -m sage.tools.cli.main"
    else
        echo -e "${WARNING} 找不到 sage CLI 工具"
        echo "$(date): 找不到 sage CLI 工具" >> "$log_file"
        return 1
    fi
    
    echo -e "${DIM}使用命令: ${SAGE_CMD} extensions install all --force${NC}"
    
    # 执行扩展安装，重定向输出到日志
    if $SAGE_CMD extensions install all --force >> "$log_file" 2>&1; then
        echo "$(date): C++扩展安装成功" >> "$log_file"
        return 0
    else
        echo "$(date): C++扩展安装失败" >> "$log_file"
        return 1
    fi
}

# 安装开发包
install_dev_packages() {
    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🛠️  开发工具安装完成${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # 记录到日志
    echo "$(date): 开发工具安装阶段" >> "$log_file"
    
    echo -e "${CHECK} 开发工具依赖已在 sage-tools[dev] 安装过程中完成"
    echo -e "${DIM}包含: black, isort, flake8, pytest, pytest-timeout, mypy, pre-commit 等${NC}"
    echo -e "${DIM}所有依赖通过 packages/sage-tools/pyproject.toml 统一管理${NC}"
    echo ""
    
    # 验证关键开发工具是否可用
    echo -e "${BOLD}  🔍 验证开发工具可用性...${NC}"
    echo ""
    
    local tools_to_check=("black" "isort" "flake8" "pytest")
    local missing_tools=()
    
    for tool in "${tools_to_check[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            echo -e "${CHECK} $tool 可用"
        else
            echo -e "${WARNING} $tool 不在 PATH 中"
            missing_tools+=("$tool")
        fi
    done
    
    # 验证关键CLI包是否可导入（这些包对Examples测试很重要）
    echo ""
    echo -e "${BOLD}  🔍 验证CLI依赖包可用性...${NC}"
    echo ""
    
    local cli_packages_to_check=("typer" "rich")
    for package in "${cli_packages_to_check[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            echo -e "${CHECK} $package 可导入"
        else
            echo -e "${WARNING} $package 无法导入"
            missing_tools+=("$package")
        fi
    done
    
    if [ ${#missing_tools[@]} -eq 0 ]; then
        echo ""
        echo -e "${CHECK} 所有开发工具验证成功！"
    else
        echo ""
        echo -e "${WARNING} 部分工具不在 PATH 中: ${missing_tools[*]}"
        echo -e "${DIM}这在某些环境中是正常的，工具仍可通过 python -m 方式使用${NC}"
    fi
    
    echo ""
    
    # 安装C++扩展（开发者模式特有）
    echo -e "${BOLD}  🧩 配置C++扩展环境（开发者模式）...${NC}"
    echo ""
    
    # 尝试安装 C++ 扩展
    if install_cpp_extensions "$log_file"; then
        echo -e "${CHECK} C++ 扩展安装成功 (sage_db, sage_flow)"
        echo -e "${DIM}现在可以使用高性能数据库和流处理功能${NC}"
    else
        echo -e "${WARNING} C++ 扩展安装失败，基础Python功能不受影响"
        echo -e "${DIM}稍后可手动安装: sage extensions install all${NC}"
        echo -e "${DIM}或查看日志了解详情: $log_file${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  🎉 开发工具安装完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # 记录到日志
    echo "$(date): 开发工具安装完成" >> "$log_file"
}
