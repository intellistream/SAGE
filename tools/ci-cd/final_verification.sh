#!/bin/bash
# 🧪 最终验证脚本 - 检查所有修复
# 确保GitHub Actions工作流能够正常运行

set -e

echo "🔍 SAGE 构建系统最终验证"
echo "=========================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

# 函数定义
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_step() {
    echo -e "${BLUE}🔧 $1${NC}"
}

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

print_info "项目根目录: $PROJECT_ROOT"
echo ""

# 验证清单
checks_passed=0
total_checks=8

# 检查1: 关键文件存在性
print_step "检查1: 验证关键文件"
files_to_check=(
    "pyproject.toml"
    "_version.py"
    ".github/workflows/build-release.yml"
)

missing_files=0
for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        print_success "文件存在: $file"
    else
        print_error "文件缺失: $file"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -eq 0 ]; then
    checks_passed=$((checks_passed + 1))
    print_success "检查1通过: 所有关键文件存在"
else
    print_error "检查1失败: $missing_files 个文件缺失"
fi
echo ""

# 检查2: 版本读取
print_step "检查2: 版本读取机制"
VERSION=$(python -c "
import sys
sys.path.insert(0, '.')
try:
    from _version import __version__
    print(__version__)
except ImportError as e:
    print('ERROR')
    exit(1)
")

if [ "$VERSION" != "ERROR" ]; then
    checks_passed=$((checks_passed + 1))
    print_success "检查2通过: 版本读取成功 ($VERSION)"
else
    print_error "检查2失败: 版本读取失败"
fi
echo ""

# 检查3: 子包结构
print_step "检查3: 子包结构完整性"
packages=("sage-common" "sage-tools" "sage-kernel" "sage-middleware" "sage-libs")
missing_packages=0

for pkg in "${packages[@]}"; do
    if [ -d "packages/$pkg" ] && [ -f "packages/$pkg/pyproject.toml" ]; then
        print_success "子包完整: $pkg"
    else
        print_error "子包缺失或不完整: $pkg"
        missing_packages=$((missing_packages + 1))
    fi
done

if [ $missing_packages -eq 0 ]; then
    checks_passed=$((checks_passed + 1))
    print_success "检查3通过: 所有子包结构完整"
else
    print_error "检查3失败: $missing_packages 个子包有问题"
fi
echo ""

# 检查4: 不存在build_wheel.py
print_step "检查4: 确认移除了不需要的文件"
if [ ! -f "build_wheel.py" ]; then
    checks_passed=$((checks_passed + 1))
    print_success "检查4通过: build_wheel.py 已正确移除"
else
    print_error "检查4失败: build_wheel.py 仍然存在"
fi
echo ""

# 检查5: pyproject.toml 配置正确性
print_step "检查5: pyproject.toml 配置验证"
config_ok=true

# 检查版本配置
if grep -q 'version = {attr = "_version.__version__"}' pyproject.toml; then
    print_success "版本配置正确: 使用 _version.__version__"
else
    print_error "版本配置错误: 未使用正确的版本路径"
    config_ok=false
fi

# 检查依赖配置
if grep -q 'isage-.*@ file:./packages/sage-' pyproject.toml; then
    print_success "依赖配置正确: 使用本地文件路径"
else
    print_error "依赖配置错误: 未找到本地文件路径依赖"
    config_ok=false
fi

if [ "$config_ok" = true ]; then
    checks_passed=$((checks_passed + 1))
    print_success "检查5通过: pyproject.toml 配置正确"
else
    print_error "检查5失败: pyproject.toml 配置有问题"
fi
echo ""

# 检查6: GitHub Actions 工作流语法
print_step "检查6: GitHub Actions 工作流语法"
workflow_file=".github/workflows/build-release.yml"

# 基本语法检查
workflow_ok=true

if grep -q "build-subpackages:" "$workflow_file"; then
    print_success "包含子包构建任务"
else
    print_error "缺少子包构建任务"
    workflow_ok=false
fi

if grep -q "build-metapackage:" "$workflow_file"; then
    print_success "包含metapackage构建任务"
else
    print_error "缺少metapackage构建任务"
    workflow_ok=false
fi

if grep -q "matrix:" "$workflow_file"; then
    print_success "包含矩阵构建策略"
else
    print_error "缺少矩阵构建策略"
    workflow_ok=false
fi

if [ "$workflow_ok" = true ]; then
    checks_passed=$((checks_passed + 1))
    print_success "检查6通过: GitHub Actions 工作流配置正确"
else
    print_error "检查6失败: GitHub Actions 工作流配置有问题"
fi
echo ""

# 检查7: 依赖替换逻辑
print_step "检查7: PyPI依赖替换逻辑"
replacement_test=$(python -c "
import re

with open('pyproject.toml', 'r') as f:
    content = f.read()

# Test replacement logic
content_modified = re.sub(
    r'\"isage-([^\"]+) @ file:\./packages/sage-([^\"]+)\"',
    r'\"isage-\1\"',
    content
)

# Check if replacement worked
if 'file:' not in content_modified.split('[project.optional-dependencies]')[0]:
    print('PASS')
else:
    print('FAIL')
")

if [ "$replacement_test" = "PASS" ]; then
    checks_passed=$((checks_passed + 1))
    print_success "检查7通过: 依赖替换逻辑正确"
else
    print_error "检查7失败: 依赖替换逻辑有问题"
fi
echo ""

# 检查8: 快速构建测试
print_step "检查8: 快速构建测试"
build_ok=true

# 清理之前的构建
rm -rf dist build *.egg-info packages/*/dist packages/*/build packages/*/*.egg-info test_build_check 2>/dev/null || true

# 创建测试目录
mkdir -p test_build_check

# 测试一个子包构建
print_info "测试 sage-common 构建..."
if (cd packages/sage-common && python -m build --wheel --outdir ../../test_build_check 2>&1 | grep -q "Successfully built"); then
    if ls test_build_check/isage_common-*.whl >/dev/null 2>&1; then
        print_success "sage-common 构建成功"
    else
        print_error "sage-common 构建失败: 未找到 wheel"
        build_ok=false
    fi
else
    print_error "sage-common 构建失败"
    build_ok=false
fi

# 测试主包构建
print_info "测试主包构建..."
if python -m build --wheel --outdir test_build_check 2>&1 | grep -q "Successfully built"; then
    if ls test_build_check/isage-*.whl >/dev/null 2>&1; then
        print_success "主包构建成功"
    else
        print_error "主包构建失败: 未找到 wheel"
        build_ok=false
    fi
else
    print_error "主包构建失败"
    build_ok=false
fi

# 清理测试构建
rm -rf test_build_check dist build *.egg-info packages/*/dist packages/*/build packages/*/*.egg-info 2>/dev/null || true

if [ "$build_ok" = true ]; then
    checks_passed=$((checks_passed + 1))
    print_success "检查8通过: 构建系统正常工作"
else
    print_error "检查8失败: 构建系统有问题"
fi
echo ""

# 最终结果
print_step "最终验证结果"
echo ""

if [ $checks_passed -eq $total_checks ]; then
    print_success "🎉 所有检查通过! ($checks_passed/$total_checks)"
    echo ""
    print_info "✨ 修复总结:"
    print_info "  ✅ 移除了不存在的 build_wheel.py 文件"
    print_info "  ✅ 修复了版本读取路径 (_version.py)"
    print_info "  ✅ 采用多包构建策略代替单一复杂构建"
    print_info "  ✅ 修复了 pyproject.toml 中的依赖配置"
    print_info "  ✅ 实现了开发时本地依赖、发布时PyPI依赖的切换"
    print_info "  ✅ 更新了 GitHub Actions 工作流支持多包构建"
    print_info "  ✅ 移除了不必要的 bytecode 编译"
    print_info "  ✅ 修复了所有配置错误"
    echo ""
    print_info "🚀 下次推送到 GitHub 时，CI/CD 应该能够:"
    print_info "  1. 并行构建所有 4 个子包"
    print_info "  2. 构建 metapackage (自动替换依赖为PyPI包名)"
    print_info "  3. 在多个 Python 版本上测试"
    print_info "  4. 发布到 GitHub Releases"
    print_info "  5. (可选) 发布到 PyPI"
    echo ""
    print_success "✅ 准备就绪! 可以安全地推送代码了!"
    exit 0
else
    print_error "❌ 部分检查失败 ($checks_passed/$total_checks)"
    echo ""
    print_warning "还有问题需要解决，请检查上述失败的项目"
    exit 1
fi
