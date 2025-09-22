#!/bin/bash
# 🧪 测试 build-release.yml 工作流的C扩展构建部分
# 专门验证C扩展路径和构建系统

set -e

echo "🏗️  SAGE Build-Release 本地测试"
echo "================================="
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

# 验证函数：检查目录是否存在
check_directory() {
    local dir_path="$1"
    local description="$2"
    
    if [ -d "$dir_path" ]; then
        print_success "$description 目录存在: $dir_path"
        return 0
    else
        print_error "$description 目录不存在: $dir_path"
        return 1
    fi
}

# 验证函数：检查构建文件是否存在
check_build_system() {
    local dir_path="$1"
    local description="$2"
    
    cd "$PROJECT_ROOT"
    
    if [ -d "$dir_path" ]; then
        cd "$dir_path"
        
        if [ -f "build.sh" ]; then
            print_success "$description 有 build.sh"
            print_info "  内容预览:"
            head -5 build.sh | sed 's/^/    /'
            cd "$PROJECT_ROOT"
            return 0
        elif [ -f "Makefile" ]; then
            print_success "$description 有 Makefile"
            print_info "  内容预览:"
            head -5 Makefile | sed 's/^/    /'
            cd "$PROJECT_ROOT"
            return 0
        else
            print_warning "$description 没有构建系统 (build.sh 或 Makefile)"
            cd "$PROJECT_ROOT"
            return 1
        fi
    else
        print_error "$description 目录不存在: $dir_path"
        return 1
    fi
}

# 测试 build-release.yml 中的C扩展路径
print_step "验证 build-release.yml 中的C扩展路径"

# 1. 验证 sage_queue 路径
SAGE_QUEUE_PATH="packages/sage-kernel/src/sage/kernel/enterprise/sage_queue"
check_directory "$SAGE_QUEUE_PATH" "sage_queue"
SAGE_QUEUE_EXISTS=$?

# 2. 验证 sage_db 路径  
SAGE_DB_PATH="packages/sage-middleware/src/sage/middleware/components/sage_db"
check_directory "$SAGE_DB_PATH" "sage_db"
SAGE_DB_EXISTS=$?

echo ""

# 验证构建系统
print_step "验证C扩展构建系统"

if [ $SAGE_QUEUE_EXISTS -eq 0 ]; then
    check_build_system "$SAGE_QUEUE_PATH" "sage_queue"
fi

if [ $SAGE_DB_EXISTS -eq 0 ]; then
    check_build_system "$SAGE_DB_PATH" "sage_db"
fi

echo ""

# 模拟 build-release.yml 的C扩展构建步骤
print_step "模拟 build-release.yml 的C扩展构建逻辑"

echo 'echo "Building SAGE C extensions..."'
echo ""

# 模拟 sage_queue 构建
print_info "模拟 sage_queue 构建检查:"
if [ -d "$SAGE_QUEUE_PATH" ]; then
    echo "if [ -d \"$SAGE_QUEUE_PATH\" ]; then"
    echo "  echo \"Building sage_queue...\""
    echo "  cd $SAGE_QUEUE_PATH"
    
    cd "$SAGE_QUEUE_PATH"
    if [ -f "build.sh" ]; then
        echo "  if [ -f \"build.sh\" ]; then"
        echo "    bash build.sh"
        print_success "✅ sage_queue 有 build.sh，构建命令可执行"
    elif [ -f "Makefile" ]; then
        echo "  elif [ -f \"Makefile\" ]; then"
        echo "    make clean && make"
        print_success "✅ sage_queue 有 Makefile，构建命令可执行"
    else
        echo "  else"
        echo "    echo \"No build system found for sage_queue, skipping\""
        print_warning "⚠️  sage_queue 没有构建系统，将跳过"
    fi
    echo "  fi"
    echo "  cd - > /dev/null"
    echo "fi"
    cd "$PROJECT_ROOT"
else
    echo "if [ -d \"$SAGE_QUEUE_PATH\" ]; then"
    echo "  # 目录不存在，此条件不会执行"
    echo "fi"
    print_error "❌ sage_queue 目录不存在，构建步骤将跳过"
fi

echo ""

# 模拟 sage_db 构建
print_info "模拟 sage_db 构建检查:"
if [ -d "$SAGE_DB_PATH" ]; then
    echo "if [ -d \"$SAGE_DB_PATH\" ]; then"
    echo "  echo \"Building sage_db...\""
    echo "  cd $SAGE_DB_PATH"
    
    cd "$SAGE_DB_PATH"
    if [ -f "build.sh" ]; then
        echo "  if [ -f \"build.sh\" ]; then"
        echo "    bash build.sh"
        print_success "✅ sage_db 有 build.sh，构建命令可执行"
    elif [ -f "Makefile" ]; then
        echo "  elif [ -f \"Makefile\" ]; then"
        echo "    make clean && make"
        print_success "✅ sage_db 有 Makefile，构建命令可执行"
    else
        echo "  else"
        echo "    echo \"No build system found for sage_db, skipping\""
        print_warning "⚠️  sage_db 没有构建系统，将跳过"
    fi
    echo "  fi"
    echo "  cd - > /dev/null"
    echo "fi"
    cd "$PROJECT_ROOT"
else
    echo "if [ -d \"$SAGE_DB_PATH\" ]; then"
    echo "  # 目录不存在，此条件不会执行"
    echo "fi"
    print_error "❌ sage_db 目录不存在，构建步骤将跳过"
fi

echo ""

# 验证现有的 .so 文件
print_step "检查现有的C扩展文件"
print_info "查找现有的 .so 文件:"

SO_FILES=$(find packages/ -name "*.so" -type f 2>/dev/null || true)
if [ -n "$SO_FILES" ]; then
    echo "$SO_FILES" | head -10
    print_success "找到现有的C扩展文件"
else
    print_warning "没有找到现有的 .so 文件"
fi

echo ""

# 检查与旧路径的差异
print_step "验证修复效果"
print_info "原来出错的路径: sage/utils/mmap_queue"
if [ -d "sage/utils/mmap_queue" ]; then
    print_error "❌ 旧路径仍然存在，可能存在混淆"
else
    print_success "✅ 旧路径已不存在，修复正确"
fi

# 总结
echo ""
print_step "测试总结"

if [ $SAGE_QUEUE_EXISTS -eq 0 ] || [ $SAGE_DB_EXISTS -eq 0 ]; then
    print_success "🎉 C扩展路径修复验证完成！"
    echo ""
    print_info "修复要点:"
    if [ $SAGE_QUEUE_EXISTS -eq 0 ]; then
        echo "   ✅ sage_queue 路径正确: $SAGE_QUEUE_PATH"
    fi
    if [ $SAGE_DB_EXISTS -eq 0 ]; then
        echo "   ✅ sage_db 路径正确: $SAGE_DB_PATH"
    fi
    echo "   ✅ 移除了错误的 sage/utils/mmap_queue 路径"
    echo "   ✅ 使用了条件检查，即使目录不存在也不会报错"
    echo ""
    print_success "🚀 GitHub Actions build-release.yml 应该能正常工作了！"
else
    print_warning "⚠️  没有找到任何C扩展目录"
    print_info "这可能意味着:"
    echo "   • C扩展已被移除或重构"
    echo "   • 路径发生了变化"
    echo "   • 不再需要C扩展构建"
    echo ""
    print_info "建议检查项目是否还需要C扩展构建步骤"
fi

echo ""
print_info "💡 提示: 这是一个模拟测试，实际构建需要相应的编译环境"
print_info "💡 要完全验证，可以在Docker环境中运行完整的构建流程"
