#!/bin/bash

# SAGE Flow 构建验证脚本
# 该脚本验证 sage-flow 在 conda activate sage 环境下的完整构建流程

set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build"
REPORT_FILE="$PROJECT_ROOT/build_test_report.txt"

# 构建配置
BUILD_TYPE="${BUILD_TYPE:-Release}"
BUILD_TESTS="${BUILD_TESTS:-ON}"
BUILD_EXAMPLES="${BUILD_EXAMPLES:-ON}"
VERBOSE="${VERBOSE:-OFF}"

# 开始构建验证
log_info "开始 SAGE Flow 构建验证..."
log_info "项目根目录: $PROJECT_ROOT"
log_info "构建目录: $BUILD_DIR"
log_info "构建类型: $BUILD_TYPE"

# 创建报告文件
cat > "$REPORT_FILE" << EOF
SAGE Flow 构建验证报告
===================
生成时间: $(date)
操作系统: $(uname -a)
项目根目录: $PROJECT_ROOT
构建类型: $BUILD_TYPE
构建目录: $BUILD_DIR

EOF

# 检查 conda 环境
check_conda_environment() {
    log_info "检查 conda 环境..."
    
    if ! command -v conda &> /dev/null; then
        log_error "conda 未安装或不在 PATH 中"
        echo "ERROR: conda 未安装" >> "$REPORT_FILE"
        return 1
    fi
    
    # 检查当前环境
    local current_env=$(conda info --envs | grep '\*' | awk '{print $1}')
    log_info "当前 conda 环境: $current_env"
    
    if [[ "$current_env" != "sage" ]]; then
        log_warning "当前不在 sage 环境中，当前环境: $current_env"
        log_info "请运行: conda activate sage"
        echo "WARNING: 不在 sage 环境中，当前环境: $current_env" >> "$REPORT_FILE"
    else
        log_success "已在 sage conda 环境中"
        echo "SUCCESS: 在 sage conda 环境中" >> "$REPORT_FILE"
    fi
    
    # 显示 conda 环境信息
    echo "Conda 环境信息:" >> "$REPORT_FILE"
    conda info >> "$REPORT_FILE" 2>&1 || true
    echo "" >> "$REPORT_FILE"
    
    return 0
}

# 验证系统依赖
check_system_dependencies() {
    log_info "检查系统依赖..."
    
    local missing_deps=()
    local deps=(
        "cmake:CMake 构建系统"
        "make:Make 构建工具"
        "g++:GNU C++ 编译器"
        "python3:Python 3 解释器"
        "pip:Python 包管理器"
    )
    
    echo "系统依赖检查:" >> "$REPORT_FILE"
    
    for dep_info in "${deps[@]}"; do
        local dep="${dep_info%%:*}"
        local desc="${dep_info#*:}"
        
        if command -v "$dep" &> /dev/null; then
            local version=$(${dep} --version 2>&1 | head -n1 || echo "版本未知")
            log_success "$desc: $version"
            echo "  ✓ $desc: $version" >> "$REPORT_FILE"
        else
            log_error "缺少依赖: $desc"
            echo "  ✗ 缺少: $desc" >> "$REPORT_FILE"
            missing_deps+=("$dep")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "缺少必要依赖: ${missing_deps[*]}"
        echo "ERROR: 缺少必要依赖: ${missing_deps[*]}" >> "$REPORT_FILE"
        return 1
    fi
    
    echo "" >> "$REPORT_FILE"
    return 0
}

# 验证 Python 依赖
check_python_dependencies() {
    log_info "检查 Python 依赖..."
    
    local python_deps=(
        "numpy:NumPy 数值计算库"
        "pybind11:Python C++ 绑定库"
    )
    
    echo "Python 依赖检查:" >> "$REPORT_FILE"
    
    for dep_info in "${python_deps[@]}"; do
        local dep="${dep_info%%:*}"
        local desc="${dep_info#*:}"
        
        if python3 -c "import $dep" &> /dev/null; then
            local version=$(python3 -c "import $dep; print($dep.__version__)" 2>/dev/null || echo "版本未知")
            log_success "$desc: $version"
            echo "  ✓ $desc: $version" >> "$REPORT_FILE"
        else
            log_error "缺少 Python 依赖: $desc"
            echo "  ✗ 缺少: $desc" >> "$REPORT_FILE"
            log_info "尝试安装: pip install $dep"
        fi
    done
    
    echo "" >> "$REPORT_FILE"
    return 0
}

# 清理构建目录
clean_build_directory() {
    log_info "清理构建目录..."
    
    if [[ -d "$BUILD_DIR" ]]; then
        log_info "删除现有构建目录: $BUILD_DIR"
        rm -rf "$BUILD_DIR"
    fi
    
    mkdir -p "$BUILD_DIR"
    log_success "构建目录已创建: $BUILD_DIR"
    
    echo "构建目录已清理并重新创建" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
}

# 配置 CMake
configure_cmake() {
    log_info "配置 CMake..."
    
    cd "$BUILD_DIR"
    
    local cmake_args=(
        "-DCMAKE_BUILD_TYPE=$BUILD_TYPE"
        "-DSAGE_FLOW_BUILD_TESTS=$BUILD_TESTS"
        "-DSAGE_FLOW_BUILD_EXAMPLES=$BUILD_EXAMPLES"
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
    )
    
    if [[ "$VERBOSE" == "ON" ]]; then
        cmake_args+=("-DCMAKE_VERBOSE_MAKEFILE=ON")
    fi
    
    echo "CMake 配置:" >> "$REPORT_FILE"
    echo "参数: ${cmake_args[*]}" >> "$REPORT_FILE"
    
    log_info "运行 CMake 配置..."
    log_info "命令: cmake ${cmake_args[*]} .."
    
    if cmake "${cmake_args[@]}" .. >> "$REPORT_FILE" 2>&1; then
        log_success "CMake 配置成功"
        echo "SUCCESS: CMake 配置成功" >> "$REPORT_FILE"
    else
        log_error "CMake 配置失败"
        echo "ERROR: CMake 配置失败" >> "$REPORT_FILE"
        return 1
    fi
    
    echo "" >> "$REPORT_FILE"
    return 0
}

# 执行构建
execute_build() {
    log_info "执行构建..."
    
    cd "$BUILD_DIR"
    
    local build_start_time=$(date +%s)
    local cpu_count=$(nproc)
    local jobs=$((cpu_count > 1 ? cpu_count - 1 : 1))
    
    echo "构建执行:" >> "$REPORT_FILE"
    echo "CPU 核心数: $cpu_count" >> "$REPORT_FILE"
    echo "并行任务数: $jobs" >> "$REPORT_FILE"
    echo "开始时间: $(date)" >> "$REPORT_FILE"
    
    log_info "使用 $jobs 个并行任务进行构建..."
    
    if make -j"$jobs" >> "$REPORT_FILE" 2>&1; then
        local build_end_time=$(date +%s)
        local build_duration=$((build_end_time - build_start_time))
        
        log_success "构建成功，耗时: ${build_duration}秒"
        echo "SUCCESS: 构建成功，耗时: ${build_duration}秒" >> "$REPORT_FILE"
    else
        log_error "构建失败"
        echo "ERROR: 构建失败" >> "$REPORT_FILE"
        return 1
    fi
    
    echo "" >> "$REPORT_FILE"
    return 0
}

# 验证构建产物
verify_build_artifacts() {
    log_info "验证构建产物..."
    
    cd "$BUILD_DIR"
    
    local expected_artifacts=(
        "libsage_flow_core.so:核心库"
        "sage_flow_datastream*.so:Python 绑定模块"
    )
    
    echo "构建产物验证:" >> "$REPORT_FILE"
    
    for artifact_info in "${expected_artifacts[@]}"; do
        local pattern="${artifact_info%%:*}"
        local desc="${artifact_info#*:}"
        
        if ls $pattern &> /dev/null; then
            local files=($(ls $pattern))
            for file in "${files[@]}"; do
                local size=$(stat -c%s "$file" 2>/dev/null || echo "未知")
                log_success "$desc: $file (大小: $size 字节)"
                echo "  ✓ $desc: $file (大小: $size 字节)" >> "$REPORT_FILE"
            done
        else
            log_error "缺少构建产物: $desc (模式: $pattern)"
            echo "  ✗ 缺少: $desc (模式: $pattern)" >> "$REPORT_FILE"
        fi
    done
    
    echo "" >> "$REPORT_FILE"
    return 0
}

# 运行代码风格检查
run_code_style_check() {
    log_info "运行代码风格检查..."

    echo "代码风格检查:" >> "$REPORT_FILE"

    # 检查 cpplint 是否可用
    if command -v cpplint &> /dev/null; then
        log_info "运行 cpplint 检查..."

        # 统计风格问题数量
        local style_errors=$(find "$PROJECT_ROOT/src" "$PROJECT_ROOT/include" \
            -name "*.cpp" -o -name "*.hpp" -o -name "*.h" | \
            xargs cpplint 2>&1 | grep -c "error\|warning" || echo "0")

        if [[ $style_errors -gt 0 ]]; then
            log_warning "发现 $style_errors 个代码风格问题"
            echo "WARNING: 发现 $style_errors 个代码风格问题" >> "$REPORT_FILE"

            # 记录主要问题类型
            echo "主要问题类型:" >> "$REPORT_FILE"
            find "$PROJECT_ROOT/src" "$PROJECT_ROOT/include" \
                -name "*.cpp" -o -name "*.hpp" -o -name "*.h" | \
                xargs cpplint 2>&1 | \
                grep "error\|warning" | \
                sed 's/.*:.*: \([a-zA-Z/]*\):.*/\1/' | \
                sort | uniq -c | sort -nr | head -10 >> "$REPORT_FILE"
        else
            log_success "代码风格检查通过"
            echo "SUCCESS: 代码风格检查通过" >> "$REPORT_FILE"
        fi
    else
        log_warning "cpplint 未安装，跳过代码风格检查"
        echo "WARNING: cpplint 未安装，跳过代码风格检查" >> "$REPORT_FILE"
    fi

    echo "" >> "$REPORT_FILE"
    return 0
}

# 运行基础测试
run_basic_tests() {
    log_info "运行基础测试..."

    cd "$BUILD_DIR"

    echo "基础测试:" >> "$REPORT_FILE"

    # 测试 Python 模块导入
    log_info "测试 Python 模块导入..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    import sage_flow_datastream
    print('SUCCESS: Python 模块导入成功')
except ImportError as e:
    print(f'ERROR: Python 模块导入失败: {e}')
    sys.exit(1)
" >> "$REPORT_FILE" 2>&1; then
        log_success "Python 模块导入测试通过"
        echo "SUCCESS: Python 模块导入测试通过" >> "$REPORT_FILE"
    else
        log_error "Python 模块导入测试失败"
        echo "ERROR: Python 模块导入测试失败" >> "$REPORT_FILE"
    fi

    # 如果构建了测试，运行 CTest
    if [[ "$BUILD_TESTS" == "ON" ]] && command -v ctest &> /dev/null; then
        log_info "运行 CTest..."
        if ctest --output-on-failure >> "$REPORT_FILE" 2>&1; then
            log_success "CTest 运行成功"
            echo "SUCCESS: CTest 运行成功" >> "$REPORT_FILE"
        else
            log_warning "CTest 运行失败或部分失败"
            echo "WARNING: CTest 运行失败或部分失败" >> "$REPORT_FILE"
        fi
    fi

    echo "" >> "$REPORT_FILE"
    return 0
}

# 生成构建总结
generate_build_summary() {
    log_info "生成构建总结..."
    
    echo "构建总结:" >> "$REPORT_FILE"
    echo "========" >> "$REPORT_FILE"
    echo "完成时间: $(date)" >> "$REPORT_FILE"
    echo "构建目录大小: $(du -sh "$BUILD_DIR" | cut -f1)" >> "$REPORT_FILE"
    
    if [[ -f "$BUILD_DIR/compile_commands.json" ]]; then
        local compile_commands_count=$(jq length "$BUILD_DIR/compile_commands.json" 2>/dev/null || echo "未知")
        echo "编译单元数量: $compile_commands_count" >> "$REPORT_FILE"
    fi
    
    echo "" >> "$REPORT_FILE"
    
    log_success "构建验证报告已生成: $REPORT_FILE"
}

# 主函数
main() {
    local start_time=$(date +%s)
    
    # 检查环境和依赖
    check_conda_environment || exit 1
    check_system_dependencies || exit 1
    check_python_dependencies || exit 1
    
    # 执行构建流程
    clean_build_directory || exit 1
    configure_cmake || exit 1
    execute_build || exit 1
    
    # 验证和测试
    verify_build_artifacts || exit 1
    run_code_style_check || exit 1
    run_basic_tests || exit 1
    
    # 生成总结
    generate_build_summary
    
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    log_success "构建验证完成！总耗时: ${total_duration}秒"
    log_info "详细报告请查看: $REPORT_FILE"
    
    echo "总耗时: ${total_duration}秒" >> "$REPORT_FILE"
    echo "构建验证完成！" >> "$REPORT_FILE"
}

# 执行主函数
main "$@"