#!/bin/bash
# SAGE 安装脚本 - 系统环境检查模块
# 全面检查系统环境、硬件配置等

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 检查操作系统及版本
check_operating_system() {
    echo -e "${INFO} 检查操作系统..."
    
    # 获取系统信息
    local os_name=""
    local os_version=""
    local is_supported=true
    
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        os_name="$NAME"
        os_version="$VERSION"
        
        # 检查是否为 Ubuntu 22.04
        if [[ "$ID" == "ubuntu" && "$VERSION_ID" == "22.04" ]]; then
            echo -e "${CHECK} 操作系统: $os_name $os_version (推荐版本)"
        elif [[ "$ID" == "ubuntu" ]]; then
            echo -e "${WARNING} 操作系统: $os_name $os_version"
            echo -e "${YELLOW}  警告: 推荐使用 Ubuntu 22.04，当前版本可能存在兼容性问题${NC}"
            is_supported=false
        else
            echo -e "${WARNING} 操作系统: $os_name $os_version"
            echo -e "${YELLOW}  警告: 推荐使用 Ubuntu 22.04，其他系统可能存在兼容性问题${NC}"
            is_supported=false
        fi
    else
        # 备用检测方法
        local uname_output=$(uname -a)
        echo -e "${WARNING} 操作系统: $uname_output"
        echo -e "${YELLOW}  警告: 无法确定系统版本，推荐使用 Ubuntu 22.04${NC}"
        is_supported=false
    fi
    
    if [ "$is_supported" = false ]; then
        echo -e "${DIM}  提示: 虽然可以继续安装，但可能遇到依赖问题${NC}"
        echo ""
    fi
    
    return 0
}

# 检查系统运行环境
check_system_runtime() {
    echo -e "${INFO} 检查系统运行环境..."
    
    local runtime_info=""
    local runtime_type=""
    local is_virtual=false
    
    # 检查 systemd-detect-virt（如果可用）
    if command -v systemd-detect-virt >/dev/null 2>&1; then
        local virt_result=$(systemd-detect-virt 2>/dev/null || echo "none")
        case "$virt_result" in
            "docker")
                runtime_info="Docker 容器"
                runtime_type="docker"
                is_virtual=true
                ;;
            "wsl")
                runtime_info="Windows Subsystem for Linux (WSL)"
                runtime_type="wsl"
                is_virtual=true
                ;;
            "kvm"|"qemu"|"vmware"|"virtualbox"|"xen")
                runtime_info="虚拟机 ($virt_result)"
                runtime_type="vm"
                is_virtual=true
                ;;
            "none")
                runtime_info="原生 Ubuntu 系统"
                runtime_type="native"
                ;;
            *)
                runtime_info="未知虚拟化环境 ($virt_result)"
                runtime_type="unknown"
                is_virtual=true
                ;;
        esac
    else
        # 手动检查各种环境标识
        if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
            runtime_info="Docker 容器"
            runtime_type="docker"
            is_virtual=true
        elif grep -qE "(Microsoft|WSL)" /proc/version 2>/dev/null; then
            # 检查是 WSL1 还是 WSL2
            if grep -q "microsoft-standard" /proc/version 2>/dev/null; then
                runtime_info="Windows Subsystem for Linux 2 (WSL2)"
                runtime_type="wsl2"
            else
                runtime_info="Windows Subsystem for Linux 1 (WSL1)"
                runtime_type="wsl1"
            fi
            is_virtual=true
        elif [ -f /proc/xen/capabilities ] 2>/dev/null; then
            runtime_info="Xen 虚拟机"
            runtime_type="vm"
            is_virtual=true
        elif dmesg 2>/dev/null | grep -qiE "(hypervisor|vmware|virtualbox|kvm)" 2>/dev/null; then
            runtime_info="虚拟机环境"
            runtime_type="vm"
            is_virtual=true
        elif [ -d /proc/vz ] && [ ! -d /proc/bc ]; then
            runtime_info="OpenVZ 容器"
            runtime_type="openvz"
            is_virtual=true
        else
            runtime_info="原生 Ubuntu 系统"
            runtime_type="native"
        fi
    fi
    
    echo -e "${CHECK} 系统运行环境: $runtime_info"
    
    # 根据环境给出详细提示
    case "$runtime_type" in
        "docker")
            echo -e "${INFO} Docker 环境检测到的特性："
            echo -e "${DIM}  - 容器化隔离环境${NC}"
            echo -e "${DIM}  - 建议确保容器有足够的资源分配 (≥4GB RAM)${NC}"
            echo -e "${DIM}  - 确保挂载了足够的存储空间${NC}"
            ;;
        "wsl1")
            echo -e "${WARNING} WSL1 环境注意事项："
            echo -e "${DIM}  - WSL1 性能较 WSL2 有限${NC}"
            echo -e "${DIM}  - 建议升级到 WSL2 以获得更好性能${NC}"
            echo -e "${DIM}  - 某些 Docker 功能可能不可用${NC}"
            ;;
        "wsl2")
            echo -e "${INFO} WSL2 环境检测到的特性："
            echo -e "${DIM}  - 完整 Linux 内核支持${NC}"
            echo -e "${DIM}  - 良好的 Docker 集成${NC}"
            echo -e "${DIM}  - 建议在 Windows 中为 WSL2 分配足够内存${NC}"
            ;;
        "vm")
            echo -e "${INFO} 虚拟机环境注意事项："
            echo -e "${DIM}  - 建议分配足够的 CPU 核心 (≥2核)${NC}"
            echo -e "${DIM}  - 建议分配足够的内存 (≥4GB)${NC}"
            echo -e "${DIM}  - 确保启用虚拟化加速功能${NC}"
            ;;
        "native")
            echo -e "${CHECK} 原生环境具有最佳性能和兼容性"
            ;;
        *)
            echo -e "${WARNING} 未知运行环境，可能影响安装兼容性"
            ;;
    esac
    
    return 0
}

# 检查CPU架构
check_cpu_architecture() {
    echo -e "${INFO} 检查CPU架构..."
    
    local arch=$(uname -m)
    local cpu_info=$(lscpu 2>/dev/null | grep "Model name" | cut -d':' -f2 | xargs || echo "未知")
    
    case "$arch" in
        "x86_64"|"amd64")
            echo -e "${CHECK} CPU架构: x86_64 (推荐架构)"
            echo -e "${DIM}  CPU型号: $cpu_info${NC}"
            ;;
        "aarch64"|"arm64")
            echo -e "${WARNING} CPU架构: ARM64 ($arch)"
            echo -e "${DIM}  CPU型号: $cpu_info${NC}"
            echo -e "${YELLOW}  警告: ARM架构可能存在某些包的兼容性问题${NC}"
            echo -e "${DIM}  提示: 部分Python包可能需要从源码编译${NC}"
            ;;
        "armv7l"|"armhf")
            echo -e "${WARNING} CPU架构: ARM32 ($arch)"
            echo -e "${DIM}  CPU型号: $cpu_info${NC}"
            echo -e "${YELLOW}  警告: ARM32架构兼容性有限，不推荐用于生产环境${NC}"
            ;;
        *)
            echo -e "${WARNING} CPU架构: $arch (未知架构)"
            echo -e "${DIM}  CPU型号: $cpu_info${NC}"
            echo -e "${YELLOW}  警告: 未知架构，可能存在严重兼容性问题${NC}"
            ;;
    esac
    
    return 0
}

# 检查GPU配置
check_gpu_configuration() {
    echo -e "${INFO} 检查GPU配置..."
    
    local has_nvidia=false
    local has_amd=false
    local gpu_info=""
    
    # 检查NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
        local nvidia_output=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$nvidia_output" ]; then
            has_nvidia=true
            echo -e "${CHECK} NVIDIA GPU 检测到:"
            echo "$nvidia_output" | while IFS=, read -r name memory; do
                echo -e "${DIM}  - $name (${memory}MB)${NC}"
            done
            
            # 检查CUDA
            if command -v nvcc &> /dev/null; then
                local cuda_version=$(nvcc --version | grep "release" | sed 's/.*release \([0-9.]*\).*/\1/')
                echo -e "${CHECK} CUDA 版本: $cuda_version"
            else
                echo -e "${WARNING} 未检测到CUDA，GPU计算功能可能受限"
            fi
        fi
    fi
    
    # 检查AMD GPU (基础检测)
    if command -v lspci >/dev/null 2>&1; then
        if lspci | grep -i "vga.*amd\|vga.*radeon" &> /dev/null; then
            has_amd=true
            local amd_gpu=$(lspci | grep -i "vga.*amd\|vga.*radeon" | head -1 | cut -d':' -f3-)
            echo -e "${CHECK} AMD GPU 检测到: $amd_gpu"
            echo -e "${DIM}  提示: ROCm支持需要额外配置${NC}"
        fi
        
        # 检查集成显卡
        if lspci | grep -i "vga.*intel" &> /dev/null; then
            local intel_gpu=$(lspci | grep -i "vga.*intel" | head -1 | cut -d':' -f3-)
            echo -e "${INFO} Intel 集成显卡: $intel_gpu"
        fi
    else
        echo -e "${DIM}  → lspci 命令不可用，跳过其他GPU设备检查${NC}"
    fi
    
    # 如果没有检测到GPU
    if [ "$has_nvidia" = false ] && [ "$has_amd" = false ]; then
        echo -e "${WARNING} 未检测到独立GPU"
        echo -e "${YELLOW}  警告: 机器学习任务性能可能受限${NC}"
        echo -e "${DIM}  提示: CPU模式仍可正常使用SAGE${NC}"
    fi
    
    return 0
}

# pip模式特定检查
check_pip_mode_requirements() {
    echo -e "${INFO} 检查pip模式要求..."
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        echo -e "${CROSS} Python3 未找到！"
        echo -e "${RED}错误: pip模式需要Python 3.11${NC}"
        return 1
    fi
    
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    local python_major=$(echo "$python_version" | cut -d'.' -f1)
    local python_minor=$(echo "$python_version" | cut -d'.' -f2)
    
    echo -e "${INFO} Python 版本: $python_version"
    
    if [ "$python_major" -eq 3 ] && [ "$python_minor" -eq 11 ]; then
        echo -e "${CHECK} Python 3.11 版本正确"
    else
        echo -e "${CROSS} Python 版本不匹配！"
        echo -e "${RED}错误: pip模式需要Python 3.11，当前版本为 $python_version${NC}"
        echo -e "${DIM}建议安装Python 3.11或使用conda模式${NC}"
        return 1
    fi
    
    # 检查pip
    if ! python3 -m pip --version &> /dev/null; then
        echo -e "${CROSS} pip 未找到！"
        echo -e "${RED}错误: 请先安装pip${NC}"
        return 1
    fi
    
    local pip_version=$(python3 -m pip --version | cut -d' ' -f2)
    echo -e "${CHECK} pip 版本: $pip_version"
    
    return 0
}

# conda模式特定检查
check_conda_mode_requirements() {
    echo -e "${INFO} 检查conda模式要求..."
    
    if ! command -v conda &> /dev/null; then
        echo -e "${CROSS} conda 未找到！"
        echo -e "${RED}错误: conda模式需要安装Anaconda或Miniconda${NC}"
        echo -e "${DIM}请访问: https://docs.conda.io/en/latest/miniconda.html${NC}"
        return 1
    fi
    
    local conda_version=$(conda --version 2>&1 | cut -d' ' -f2)
    echo -e "${CHECK} conda 版本: $conda_version"
    
    # 检查当前环境
    local current_env=$(conda env list | grep '\*' | awk '{print $1}')
    echo -e "${INFO} 当前conda环境: $current_env"
    
    # 检查conda配置
    local conda_info=$(conda info --json 2>/dev/null)
    if [ $? -eq 0 ]; then
        local python_version=$(echo "$conda_info" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('python_version', 'unknown'))" 2>/dev/null)
        if [ -n "$python_version" ] && [ "$python_version" != "unknown" ]; then
            echo -e "${CHECK} conda环境Python版本: $python_version"
        fi
    fi
    
    return 0
}

# 执行通用系统检查
run_general_system_check() {
    echo ""
    echo -e "${GEAR} ${BOLD}系统环境检查${NC}"
    echo ""
    
    check_operating_system
    check_system_environment
    check_cpu_architecture
    check_gpu_configuration
    
    echo ""
}

# 执行特定模式检查
run_mode_specific_check() {
    local install_environment="$1"
    
    echo -e "${GEAR} ${BOLD}${install_environment}模式环境检查${NC}"
    echo ""
    
    case "$install_environment" in
        "pip")
            if ! check_pip_mode_requirements; then
                echo -e "${CROSS} pip模式环境检查失败"
                exit 1
            fi
            ;;
        "conda")
            if ! check_conda_mode_requirements; then
                echo -e "${CROSS} conda模式环境检查失败"
                exit 1
            fi
            ;;
        *)
            echo -e "${WARNING} 未知安装环境: $install_environment"
            return 1
            ;;
    esac
    
    echo -e "${CHECK} ${install_environment}模式环境检查通过"
    echo ""
}
