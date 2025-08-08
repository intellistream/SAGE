#!/bin/bash

# SAGE Core 快速启动脚本
# 以开发模式安装 sage-core 源代码，并安装闭源依赖包

set -e

# 获取脚本所在目录
SAGE_CORE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SAGE_CORE_ROOT/../.." && pwd)"

echo "SAGE Core 目录: $SAGE_CORE_ROOT"
echo "项目根目录: $PROJECT_ROOT"

# 引入工具模块（如果存在）
if [ -f "$PROJECT_ROOT/scripts/logging.sh" ]; then
    source "$PROJECT_ROOT/scripts/logging.sh"
    source "$PROJECT_ROOT/scripts/common_utils.sh"
    source "$PROJECT_ROOT/scripts/conda_utils.sh"
else
    # 简单的日志函数（如果没有工具模块）
    print_header() { echo -e "\n\033[1;34m=== $1 ===\033[0m"; }
    print_status() { echo -e "\033[1;33m[INFO]\033[0m $1"; }
    print_success() { echo -e "\033[1;32m[SUCCESS]\033[0m $1"; }
    print_error() { echo -e "\033[1;31m[ERROR]\033[0m $1"; }
    print_warning() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
fi

# 脚本开始
print_header "🌟 SAGE Core 开发环境快速启动"

# 检查基本命令
if ! command -v python3 >/dev/null 2>&1; then
    print_error "python3 未安装，请先安装 Python 3.10+"
    exit 1
fi

if ! command -v pip >/dev/null 2>&1; then
    print_error "pip 未安装，请先安装 pip"
    exit 1
fi

# 检查 Python 版本
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.10"
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    print_error "Python 版本 $python_version 不满足要求 (>= $required_version)"
    exit 1
fi

print_success "Python 版本检查通过: $python_version"

# 切换到 sage-core 目录
cd "$SAGE_CORE_ROOT"
print_status "当前目录: $SAGE_CORE_ROOT"

# 检查项目结构
if [ ! -f "pyproject.toml" ]; then
    print_error "未找到 pyproject.toml，请确保在 sage-core 包目录中运行此脚本"
    exit 1
fi

if [ ! -d "src/sage" ]; then
    print_error "未找到 src/sage 目录，请确保项目结构完整"
    exit 1
fi

print_success "确认在 SAGE Core 包目录"

# 询问用户是否继续
echo
echo "本脚本将："
echo "1) 以开发模式 (-e) 安装当前 sage-core 源代码"
echo "2) 通过 pyproject.toml 从 PyPI 安装闭源依赖包: sage-utils, sage-kernel, sage-middleware"
echo "3) 安装其他必要的依赖包"
echo
read -p "是否继续? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    print_status "操作取消"
    exit 0
fi

# 开始安装过程
print_header "📦 开始安装 SAGE Core 开发环境"

# 升级 pip
print_status "升级 pip..."
pip install --upgrade pip

# 清理可能的冲突包
print_status "清理可能的包冲突..."
pip list | grep -E "^sage" | awk '{print $1}' | xargs -r pip uninstall -y 2>/dev/null || true
pip list | grep -E "^intellistream-sage" | awk '{print $1}' | xargs -r pip uninstall -y 2>/dev/null || true

# 以开发模式安装当前 sage-core 包（这会自动从 PyPI 安装依赖包）
print_status "以开发模式安装 sage-core（包含 PyPI 闭源依赖）..."
if ! pip install -e .; then
    print_error "sage-core 开发安装失败"
    exit 1
fi

# 验证安装
print_header "🔍 验证安装结果"

print_status "检查安装的包..."
pip list | grep -E "(sage|intellistream-sage)" || print_warning "未找到相关包"

print_status "测试 sage 模块导入..."
if python3 -c "import sage; print('✅ sage 模块导入成功')" 2>/dev/null; then
    print_success "sage 模块导入测试通过"
else
    print_warning "sage 模块导入失败，可能需要检查依赖"
fi

# 显示安装完成信息
print_header "🎉 SAGE Core 开发环境安装完成！"

echo
echo "安装摘要:"
echo "✅ sage-core 已以开发模式安装 (可直接编辑源代码)"
echo "📦 依赖包已从 PyPI 安装 (闭源版本)"
echo "🔧 sage-utils, sage-kernel, sage-middleware 为闭源包"
echo
echo "使用说明:"
echo "1) 现在可以直接编辑 src/sage/ 下的源代码"
echo "2) sage-core 代码修改会立即生效，无需重新安装"
echo "3) 可以使用 'python -c \"import sage\"' 测试模块"
echo "4) 依赖包为 PyPI 闭源版本，提供稳定功能"
echo
echo "开发模式特点:"
echo "• sage-core 源代码修改立即生效"
echo "• 可以直接调试和开发核心 API"
echo "• 依赖包使用稳定的 PyPI 闭源版本"
echo "• 适合 sage-core 核心功能开发"
echo

print_success "开发环境准备就绪！"
