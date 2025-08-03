#!/bin/bash
"""
SAGE迁移助手脚本
===============

一键执行完整的SAGE项目迁移流程。
"""
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' {1..60})${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

# 脚本参数
SOURCE_REPO=""
TARGET_DIR=""
MIGRATION_PHASE="all"
SKIP_ANALYSIS=false
SKIP_SPLIT=false
SKIP_REFACTOR=false
DRY_RUN=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --source-repo|-s)
            SOURCE_REPO="$2"
            shift 2
            ;;
        --target-dir|-t)
            TARGET_DIR="$2"
            shift 2
            ;;
        --phase|-p)
            MIGRATION_PHASE="$2"
            shift 2
            ;;
        --skip-analysis)
            SKIP_ANALYSIS=true
            shift
            ;;
        --skip-split)
            SKIP_SPLIT=true
            shift
            ;;
        --skip-refactor)
            SKIP_REFACTOR=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "SAGE迁移助手脚本"
            echo ""
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --source-repo, -s PATH    源仓库路径 (必需)"
            echo "  --target-dir, -t PATH     目标目录路径 (必需)"
            echo "  --phase, -p PHASE         迁移阶段 (all|analysis|split|refactor)"
            echo "  --skip-analysis           跳过代码分析阶段"
            echo "  --skip-split             跳过项目分割阶段"
            echo "  --skip-refactor          跳过命名空间重构阶段"
            echo "  --dry-run                干运行模式，不执行实际操作"
            echo "  --help, -h               显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 -s /path/to/api-rework -t /path/to/output"
            echo "  $0 -s . -t ../sage-migration --phase analysis"
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 验证必需参数
if [[ -z "$SOURCE_REPO" ]]; then
    print_error "必须指定源仓库路径 (--source-repo)"
    exit 1
fi

if [[ -z "$TARGET_DIR" ]]; then
    print_error "必须指定目标目录路径 (--target-dir)"
    exit 1
fi

# 验证路径
if [[ ! -d "$SOURCE_REPO" ]]; then
    print_error "源仓库路径不存在: $SOURCE_REPO"
    exit 1
fi

if [[ ! -d "$SOURCE_REPO/.git" ]]; then
    print_error "源路径不是Git仓库: $SOURCE_REPO"
    exit 1
fi

# 转换为绝对路径
SOURCE_REPO=$(cd "$SOURCE_REPO" && pwd)
TARGET_DIR=$(cd "$(dirname "$TARGET_DIR")" && pwd)/$(basename "$TARGET_DIR")

print_header "🚀 SAGE项目迁移助手"
echo "📂 源仓库: $SOURCE_REPO"
echo "📁 目标目录: $TARGET_DIR"
echo "🎯 迁移阶段: $MIGRATION_PHASE"
echo "🔍 干运行模式: $DRY_RUN"
echo ""

# 创建目标目录
if [[ "$DRY_RUN" == "false" ]]; then
    mkdir -p "$TARGET_DIR"
fi

# 检查Python和依赖
check_dependencies() {
    print_step "检查依赖环境..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "未找到Python 3"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_info "Python版本: $python_version"
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        print_error "未找到Git"
        exit 1
    fi
    
    git_version=$(git --version)
    print_info "$git_version"
    
    # 检查迁移工具
    migration_tools_dir="$SOURCE_REPO/migration-tools"
    if [[ ! -d "$migration_tools_dir" ]]; then
        print_error "未找到迁移工具目录: $migration_tools_dir"
        exit 1
    fi
    
    print_success "依赖环境检查完成"
}

# 阶段1: 代码结构分析
run_analysis_phase() {
    if [[ "$SKIP_ANALYSIS" == "true" ]] && [[ "$MIGRATION_PHASE" != "analysis" ]]; then
        print_info "跳过代码分析阶段"
        return
    fi
    
    print_header "📊 阶段1: 代码结构分析"
    
    analysis_output="$TARGET_DIR/analysis"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "$analysis_output"
        
        print_step "分析项目结构..."
        cd "$SOURCE_REPO"
        python3 migration-tools/analyze_structure.py \
            --project-root . \
            --output-dir "$analysis_output" \
            --detailed
        
        print_success "代码分析完成"
        print_info "分析结果保存在: $analysis_output"
    else
        print_info "[DRY RUN] 将执行代码结构分析"
    fi
}

# 阶段2: 项目分割
run_split_phase() {
    if [[ "$SKIP_SPLIT" == "true" ]] && [[ "$MIGRATION_PHASE" != "split" ]]; then
        print_info "跳过项目分割阶段"
        return
    fi
    
    print_header "✂️  阶段2: 项目分割"
    
    split_output="$TARGET_DIR/split-projects"
    migration_plan="$TARGET_DIR/analysis/migration_plan.json"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "$split_output"
        
        if [[ ! -f "$migration_plan" ]]; then
            print_warning "未找到迁移计划文件，将使用默认配置"
            migration_plan=""
        fi
        
        print_step "分割项目..."
        cd "$SOURCE_REPO"
        
        # 分割各个项目
        projects=("sage-core" "sage-extensions" "sage-dashboard")
        for project in "${projects[@]}"; do
            print_info "分割项目: $project"
            python3 migration-tools/split_project.py \
                --source-repo . \
                --target-dir "$split_output" \
                --project "$project"
        done
        
        print_success "项目分割完成"
        print_info "分割结果保存在: $split_output"
    else
        print_info "[DRY RUN] 将执行项目分割"
    fi
}

# 阶段3: 命名空间重构
run_refactor_phase() {
    if [[ "$SKIP_REFACTOR" == "true" ]] && [[ "$MIGRATION_PHASE" != "refactor" ]]; then
        print_info "跳过命名空间重构阶段"
        return
    fi
    
    print_header "🔄 阶段3: 命名空间重构"
    
    split_output="$TARGET_DIR/split-projects"
    refactor_output="$TARGET_DIR/refactor-reports"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "$refactor_output"
        
        # 重构各个项目
        projects=("sage-core" "sage-extensions" "sage-dashboard")
        for project in "${projects[@]}"; do
            project_path="$split_output/$project"
            if [[ -d "$project_path" ]]; then
                print_info "重构项目: $project"
                python3 "$SOURCE_REPO/migration-tools/refactor_namespace.py" \
                    --project-path "$project_path" \
                    --target-project "$project" \
                    --create-structure \
                    --update-imports \
                    --output-report "$refactor_output/${project}-refactor-report.json"
            else
                print_warning "项目路径不存在，跳过: $project_path"
            fi
        done
        
        print_success "命名空间重构完成"
        print_info "重构报告保存在: $refactor_output"
    else
        print_info "[DRY RUN] 将执行命名空间重构"
    fi
}

# 生成迁移总结报告
generate_migration_summary() {
    print_header "📋 生成迁移总结报告"
    
    summary_file="$TARGET_DIR/migration-summary.md"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        cat > "$summary_file" << EOF
# SAGE项目迁移总结报告

## 📊 迁移概览

- **源仓库**: $SOURCE_REPO
- **目标目录**: $TARGET_DIR
- **迁移时间**: $(date '+%Y-%m-%d %H:%M:%S')
- **迁移阶段**: $MIGRATION_PHASE

## 📁 输出结构

\`\`\`
$TARGET_DIR/
├── analysis/                    # 代码结构分析结果
│   ├── project_analysis.json   # 项目分析报告
│   ├── migration_plan.json     # 迁移计划
│   └── detailed_modules.json   # 详细模块信息
├── split-projects/              # 分割后的项目
│   ├── sage-core/              # Python核心框架
│   ├── sage-extensions/        # C++扩展
│   └── sage-dashboard/         # Web界面
├── refactor-reports/            # 重构报告
│   ├── sage-core-refactor-report.json
│   ├── sage-extensions-refactor-report.json
│   └── sage-dashboard-refactor-report.json
└── migration-summary.md        # 本文件
\`\`\`

## 🎯 下一步操作

### 1. 创建GitHub仓库
\`\`\`bash
# 在GitHub上创建以下仓库:
# - intellistream/SAGE (主仓库)
# - intellistream/sage-core
# - intellistream/sage-extensions
# - intellistream/sage-dashboard
\`\`\`

### 2. 推送分割后的项目
\`\`\`bash
cd $TARGET_DIR/split-projects/sage-core
git remote add origin https://github.com/intellistream/sage-core.git
git push -u origin main

cd ../sage-extensions
git remote add origin https://github.com/intellistream/sage-extensions.git
git push -u origin main

cd ../sage-dashboard
git remote add origin https://github.com/intellistream/sage-dashboard.git
git push -u origin main
\`\`\`

### 3. 创建主仓库并配置submodules
\`\`\`bash
# 创建主仓库
mkdir SAGE && cd SAGE
git init
git remote add origin https://github.com/intellistream/SAGE.git

# 添加submodules
git submodule add https://github.com/intellistream/sage-core.git sage-core
git submodule add https://github.com/intellistream/sage-extensions.git sage-extensions
git submodule add https://github.com/intellistream/sage-dashboard.git sage-dashboard

# 提交并推送
git add .
git commit -m "Initial commit with submodules"
git push -u origin main
\`\`\`

### 4. 测试和验证
\`\`\`bash
# 测试各个组件的安装和功能
cd sage-core && pip install -e . && cd ..
cd sage-extensions && pip install -e . && cd ..
cd sage-dashboard/backend && pip install -e . && cd ../..

# 运行集成测试
python3 -c "
import sage
print(f'Available modules: {sage.get_available_modules()}')
print(f'Extensions: {sage.check_extensions()}')
"
\`\`\`

## ⚠️  注意事项

1. **版本兼容性**: 确保各组件版本兼容
2. **测试覆盖**: 运行完整的测试套件
3. **文档更新**: 更新安装和使用文档
4. **CI/CD配置**: 配置各仓库的持续集成
5. **依赖管理**: 检查和更新依赖关系

## 📞 支持

如有问题，请联系SAGE开发团队或提交Issue。

EOF

        print_success "迁移总结报告已生成: $summary_file"
    else
        print_info "[DRY RUN] 将生成迁移总结报告"
    fi
}

# 主执行流程
main() {
    print_info "开始SAGE项目迁移..."
    
    # 检查依赖
    check_dependencies
    
    # 根据阶段参数执行不同操作
    case $MIGRATION_PHASE in
        "all")
            run_analysis_phase
            run_split_phase
            run_refactor_phase
            generate_migration_summary
            ;;
        "analysis")
            run_analysis_phase
            ;;
        "split")
            run_split_phase
            ;;
        "refactor")
            run_refactor_phase
            ;;
        *)
            print_error "未知的迁移阶段: $MIGRATION_PHASE"
            print_info "支持的阶段: all, analysis, split, refactor"
            exit 1
            ;;
    esac
    
    print_header "🎉 迁移完成！"
    print_info "详细信息请查看: $TARGET_DIR"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "这是干运行模式，未执行实际操作"
        print_info "移除 --dry-run 参数以执行实际迁移"
    fi
}

# 执行主函数
main
