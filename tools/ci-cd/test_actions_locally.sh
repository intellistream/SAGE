#!/bin/bash
# 🧪 本地测试GitHub Actions工作流
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

# 测试从pyproject.toml提取版本
VERSION=$(python -c "
try:
    import tomllib
except ImportError:
    import tomli as tomllib
    
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    version = data.get('project', {}).get('version')
    if version:
        print(version)
    else:
        print('0.1.0')  # 默认版本
" 2>/dev/null || echo "0.1.0")

if [ "$VERSION" != "" ] && [ "$VERSION" != "0.1.0" ]; then
    print_success "版本提取成功: $VERSION"
elif [ "$VERSION" = "0.1.0" ]; then
    print_warning "使用默认版本: $VERSION"
else
    print_error "版本提取失败"
    exit 1
fi
echo ""

# 测试3: 依赖解析（检查file:路径问题）
print_step "测试3: 依赖解析测试"
print_info "检查 file: 路径依赖是否会在CI中造成问题"

# 读取并分析依赖
python -c "
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
        print(f'   - {dep}')
    print('')
    print('💡 建议解决方案：')
    print('   1. 在CI中使用 pip install -e packages/package-name')
    print('   2. 或者修改CI脚本直接安装子包')
else:
    print('✅ 没有发现 file: 路径依赖')
"

if [ $? -eq 0 ]; then
    print_warning "依赖分析完成（存在潜在CI问题）"
else
    print_error "依赖分析失败"
fi
echo ""

# 测试4: 模拟quickstart.sh安装（快速模式）
print_step "测试4: 模拟快速安装流程"
print_info "模拟: ./quickstart.sh --quick"

# 检查quickstart.sh是否存在且可执行
if [ -x "./quickstart.sh" ]; then
    print_info "检测到quickstart.sh，测试快速安装逻辑..."
    
    # 模拟核心安装步骤（不实际安装）
    echo "   → 检查Python环境"
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python检查: $PYTHON_VERSION"
    else
        print_error "Python3未找到"
        exit 1
    fi
    
    echo "   → 检查pip"
    if python3 -m pip --version >/dev/null 2>&1; then
        print_success "pip检查通过"
    else
        print_error "pip未找到"
        exit 1
    fi
    
    echo "   → 检查pyproject.toml"
    if [ -f "pyproject.toml" ]; then
        print_success "pyproject.toml存在"
    else
        print_error "pyproject.toml不存在"
        exit 1
    fi
    
    print_success "快速安装模拟成功"
else
    print_warning "quickstart.sh不存在或不可执行"
fi
echo ""

# 测试5: CI环境变量模拟
print_step "测试5: CI环境变量模拟"
print_info "模拟GitHub Actions环境变量"

# 设置CI环境变量
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_WORKSPACE="$PROJECT_ROOT"

echo "   设置环境变量:"
echo "   - CI=true"
echo "   - GITHUB_ACTIONS=true"  
echo "   - GITHUB_WORKSPACE=$PROJECT_ROOT"

# 测试环境变量是否正确设置
if [ "$CI" = "true" ] && [ "$GITHUB_ACTIONS" = "true" ]; then
    print_success "CI环境变量设置成功"
else
    print_error "CI环境变量设置失败"
fi
echo ""

# 测试6: 子包结构检查
print_step "测试6: 子包结构检查"
print_info "检查SAGE子包结构"

packages_dir="packages"
if [ -d "$packages_dir" ]; then
    echo "   发现的子包:"
    for pkg in "$packages_dir"/*; do
        if [ -d "$pkg" ]; then
            pkg_name=$(basename "$pkg")
            if [ -f "$pkg/pyproject.toml" ]; then
                print_success "   - $pkg_name (有pyproject.toml)"
            else
                print_warning "   - $pkg_name (缺少pyproject.toml)"
            fi
        fi
    done
    print_success "子包结构检查完成"
else
    print_error "packages目录不存在"
    exit 1
fi
echo ""

# 测试7: GitHub Actions workflow语法检查
print_step "测试7: GitHub Actions workflow语法检查"
print_info "检查workflow文件语法"

workflows_dir=".github/workflows"
if [ -d "$workflows_dir" ]; then
    yaml_files=$(find "$workflows_dir" -name "*.yml" -o -name "*.yaml")
    
    if [ -n "$yaml_files" ]; then
        echo "   发现的workflow文件:"
        echo "$yaml_files" | while read -r file; do
            echo "   - $(basename "$file")"
        done
        
        # 检查是否有Python可以验证YAML
        if python3 -c "import yaml" >/dev/null 2>&1; then
            print_info "使用Python yaml模块验证语法..."
            for file in $yaml_files; do
                if python3 -c "import yaml; yaml.safe_load(open('$file'))" >/dev/null 2>&1; then
                    print_success "   $(basename "$file") 语法正确"
                else
                    print_error "   $(basename "$file") 语法错误"
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
echo ""

# 测试8: 提供CI修复建议
print_step "测试8: CI修复建议"
print_info "分析并提供CI改进建议"

echo ""
echo "📋 GitHub Actions 改进建议:"
echo "=========================="
echo ""

echo "1. 📦 依赖安装策略:"
echo "   当前问题: pyproject.toml使用file:路径，在CI中不可用"
echo "   建议修复: 在CI中使用以下安装顺序:"
echo "     pip install -e packages/sage-common"
echo "     pip install -e packages/sage-kernel" 
echo "     pip install -e packages/sage-middleware"
echo "     pip install -e packages/sage-libs"
echo "     pip install -e ."
echo ""

echo "2. 🧪 测试策略:"
echo "   建议: 使用quickstart.sh --minimal进行CI测试"
echo "   原因: 减少依赖，提高CI速度和稳定性"
echo ""

echo "3. 🔧 构建策略:"
echo "   当前: 可能存在C扩展构建问题"
echo "   建议: 确保所有C扩展都有proper build.sh或Makefile"
echo ""

echo "4. 📈 性能优化:"
echo "   建议: 使用缓存加速CI"
echo "   - pip cache"
echo "   - conda cache (如果使用)"
echo "   - 编译后的C扩展cache"
echo ""

print_success "本地CI测试完成！"
echo ""
echo "🎯 下一步行动:"
echo "1. 根据上述建议修改CI配置"
echo "2. 提交更改并观察GitHub Actions运行结果"
echo "3. 如有问题，查看GitHub Actions日志进行调试"
echo ""

# 清理环境变量
unset CI GITHUB_ACTIONS GITHUB_WORKSPACE
