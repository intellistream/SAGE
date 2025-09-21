#!/bin/bash
# 🧪 本地测试GitHub Actions工作流（Legacy Diagnostic Script）
# 这个脚本模拟GitHub Actions环境，测试我们的CI/CD配置

set -e

echo "🚀 SAGE GitHub Actions 本地测试"
echo "=================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

# 函数定义
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_step() { echo -e "${BLUE}🔧 $1${NC}"; }

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$PROJECT_ROOT"

echo "📁 项目根目录: $PROJECT_ROOT"
echo ""

# 测试1: 基础依赖安装（模拟GitHub Actions步骤）
print_step "测试1: 基础依赖安装"
print_info "模拟: Install build dependencies"

if pip install build setuptools wheel tomli >/dev/null 2>&1; then
    print_success "基础依赖安装成功"
else
    print_error "基础依赖安装失败"
    exit 1
fi
echo ""

# 测试2: 版本提取（模拟GitHub Actions中的版本获取）
print_step "测试2: 版本提取测试"
print_info "模拟: Get version step"

VERSION=$(python -c "
try:
    import tomllib
except ImportError:
    import tomli as tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    version = data.get('project', {}).get('version')
    print(version or '0.1.0')
" 2>/dev/null || echo "0.1.0")

if [ -n "$VERSION" ]; then
    print_success "版本提取结果: $VERSION"
else
    print_error "版本提取失败"
    exit 1
fi
echo ""

# 测试3: 依赖解析（检查file:路径问题）
print_step "测试3: 依赖解析测试"
print_info "检查 file: 路径依赖是否会在CI中造成问题"

python - <<'PY'
try:
    import tomllib
except ImportError:
    import tomli as tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
deps = data.get('project', {}).get('dependencies', [])
file_deps = [dep for dep in deps if 'file:' in dep]
if file_deps:
    print('⚠️  发现 file: 路径依赖（在GitHub Actions中可能有问题）:')
    for dep in file_deps:
        print('   -', dep)
    print('\n💡 建议：在CI中使用 pip install -e packages/<name> 顺序安装子包')
else:
    print('✅ 没有发现 file: 路径依赖')
PY
echo ""

# 测试4: 模拟quickstart.sh安装（快速模式）
print_step "测试4: 模拟快速安装流程"
print_info "模拟: ./quickstart.sh --quick"

if [ -x "./quickstart.sh" ]; then
    print_info "检测到quickstart.sh，测试快速安装逻辑..."
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python检查: $PYTHON_VERSION"
    else
        print_error "Python3未找到"; exit 1
    fi
    if python3 -m pip --version >/dev/null 2>&1; then
        print_success "pip检查通过"
    else
        print_error "pip未找到"; exit 1
    fi
    if [ -f "pyproject.toml" ]; then
        print_success "pyproject.toml存在"
    else
        print_error "pyproject.toml不存在"; exit 1
    fi
    print_success "快速安装模拟成功"
else
    print_warning "quickstart.sh不存在或不可执行"
fi
echo ""

# 测试5: CI环境变量模拟
print_step "测试5: CI环境变量模拟"
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_WORKSPACE="$PROJECT_ROOT"
echo "   - CI=$CI"; echo "   - GITHUB_ACTIONS=$GITHUB_ACTIONS"; echo "   - GITHUB_WORKSPACE=$GITHUB_WORKSPACE"
print_success "CI环境变量设置完成"
echo ""

# 测试6: 子包结构检查
print_step "测试6: 子包结构检查"
packages_dir="packages"
if [ -d "$packages_dir" ]; then
    echo "   发现的子包:"
    for pkg in "$packages_dir"/*; do
        [ -d "$pkg" ] || continue
        pkg_name=$(basename "$pkg")
        if [ -f "$pkg/pyproject.toml" ]; then
            print_success "   - $pkg_name (有pyproject.toml)"
        else
            print_warning "   - $pkg_name (缺少pyproject.toml)"
        fi
    done
    print_success "子包结构检查完成"
else
    print_error "packages目录不存在"; exit 1
fi
echo ""

# 测试7: Workflow语法检查（可选，若有pyyaml）
print_step "测试7: Workflow语法检查"
workflows_dir=".github/workflows"
if [ -d "$workflows_dir" ]; then
    yaml_files=$(find "$workflows_dir" -name "*.yml" -o -name "*.yaml")
    if [ -n "$yaml_files" ]; then
        if python3 -c "import yaml" >/dev/null 2>&1; then
            for file in $yaml_files; do
                if python3 -c "import yaml; yaml.safe_load(open('$file'))" >/dev/null 2>&1; then
                    print_success "$(basename "$file") 语法正确"
                else
                    print_error "$(basename "$file") 语法错误"
                fi
            done
        else
            print_warning "yaml模块未安装，跳过语法检查"
        fi
    else
        print_warning "未找到workflow文件"
    fi
else
    print_warning ".github/workflows目录不存在"
fi

print_success "本地CI诊断完成 (legacy)"
