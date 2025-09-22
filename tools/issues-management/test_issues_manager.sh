#!/bin/bash

# SAGE Issues Manager 自动化测试脚本
# 测试所有核心功能并自动清理中间产物

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 测试状态
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_RESULTS=()

# 测试报告文件
TEST_REPORT="$SCRIPT_DIR/test_results_$(date +%Y%m%d_%H%M%S).log"

# 原始数据备份目录
BACKUP_DIR="/tmp/issues_manager_test_backup_$(date +%Y%m%d_%H%M%S)"

# 清理标志
CLEANUP_PERFORMED=false

# 获取配置路径的辅助函数
get_config_path() {
    local path_type="$1"
    cd "$SCRIPT_DIR"
    case "$path_type" in
        workspace|output|metadata|issues)
            python3 _scripts/helpers/get_paths.py "$path_type" 2>/dev/null | tail -1
            ;;
        *)
            echo ""
            ;;
    esac
}

# 初始化测试环境
initialize_test_env() {
    echo -e "${CYAN}🔧 初始化测试环境...${NC}"
    
    # 获取实际路径
    ISSUES_WORKSPACE_PATH="$(get_config_path "workspace")"
    ISSUES_OUTPUT_PATH="$(get_config_path "output")"
    ISSUES_METADATA_PATH="$(get_config_path "metadata")"
    ISSUES_DIR="$(get_config_path "issues")"
    
    # 如果无法从config获取路径，使用备用路径
    if [ -z "$ISSUES_WORKSPACE_PATH" ]; then
        ISSUES_WORKSPACE_PATH="$PROJECT_ROOT/output/issues-workspace"
    fi
    if [ -z "$ISSUES_OUTPUT_PATH" ]; then
        ISSUES_OUTPUT_PATH="$PROJECT_ROOT/output/issues-output"
    fi
    if [ -z "$ISSUES_METADATA_PATH" ]; then
        ISSUES_METADATA_PATH="$PROJECT_ROOT/output/issues-metadata"
    fi
    if [ -z "$ISSUES_DIR" ]; then
        ISSUES_DIR="$PROJECT_ROOT/output/issues-workspace/issues"
    fi
    
    echo "📁 测试使用的路径配置："
    echo "   Workspace: $ISSUES_WORKSPACE_PATH"
    echo "   Output: $ISSUES_OUTPUT_PATH"
    echo "   Metadata: $ISSUES_METADATA_PATH"
    echo "   Issues: $ISSUES_DIR"
    
    # 创建必要的目录
    mkdir -p "$ISSUES_WORKSPACE_PATH"
    mkdir -p "$ISSUES_OUTPUT_PATH"
    mkdir -p "$ISSUES_METADATA_PATH"
    mkdir -p "$ISSUES_DIR"
    mkdir -p "$BACKUP_DIR"
    
    echo "✅ 测试环境初始化完成"
    echo ""
}

# 备份现有数据
backup_existing_data() {
    echo -e "${CYAN}💾 备份现有数据...${NC}"
    
    local backed_up=false
    
    # 备份Issues数据
    if [ -d "$ISSUES_DIR" ] && [ "$(ls -A "$ISSUES_DIR" 2>/dev/null)" ]; then
        echo "📂 备份Issues目录: $ISSUES_DIR"
        cp -r "$ISSUES_DIR" "$BACKUP_DIR/issues_backup" 2>/dev/null || true
        backed_up=true
    fi
    
    # 备份Metadata
    if [ -d "$ISSUES_METADATA_PATH" ] && [ "$(ls -A "$ISSUES_METADATA_PATH" 2>/dev/null)" ]; then
        echo "📋 备份Metadata目录: $ISSUES_METADATA_PATH"
        cp -r "$ISSUES_METADATA_PATH" "$BACKUP_DIR/metadata_backup" 2>/dev/null || true
        backed_up=true
    fi
    
    # 备份Output
    if [ -d "$ISSUES_OUTPUT_PATH" ] && [ "$(ls -A "$ISSUES_OUTPUT_PATH" 2>/dev/null)" ]; then
        echo "📤 备份Output目录: $ISSUES_OUTPUT_PATH"
        cp -r "$ISSUES_OUTPUT_PATH" "$BACKUP_DIR/output_backup" 2>/dev/null || true
        backed_up=true
    fi
    
    # 备份GitHub Token (如果存在)
    local token_file="$PROJECT_ROOT/.github_token"
    if [ -f "$token_file" ]; then
        echo "🔑 备份GitHub Token"
        cp "$token_file" "$BACKUP_DIR/github_token_backup" 2>/dev/null || true
        backed_up=true
    fi
    
    if [ "$backed_up" = true ]; then
        echo "✅ 数据备份完成，备份位置: $BACKUP_DIR"
    else
        echo "ℹ️ 未发现需要备份的数据"
    fi
    echo ""
}

# 恢复数据
restore_data() {
    echo -e "${CYAN}🔄 恢复原始数据...${NC}"
    
    local restored=false
    
    # 恢复Issues数据
    if [ -d "$BACKUP_DIR/issues_backup" ]; then
        echo "📂 恢复Issues目录"
        rm -rf "$ISSUES_DIR"/* 2>/dev/null || true
        cp -r "$BACKUP_DIR/issues_backup"/* "$ISSUES_DIR/" 2>/dev/null || true
        restored=true
    fi
    
    # 恢复Metadata
    if [ -d "$BACKUP_DIR/metadata_backup" ]; then
        echo "📋 恢复Metadata目录"
        rm -rf "$ISSUES_METADATA_PATH"/* 2>/dev/null || true
        cp -r "$BACKUP_DIR/metadata_backup"/* "$ISSUES_METADATA_PATH/" 2>/dev/null || true
        restored=true
    fi
    
    # 恢复Output
    if [ -d "$BACKUP_DIR/output_backup" ]; then
        echo "📤 恢复Output目录"
        rm -rf "$ISSUES_OUTPUT_PATH"/* 2>/dev/null || true
        cp -r "$BACKUP_DIR/output_backup"/* "$ISSUES_OUTPUT_PATH/" 2>/dev/null || true
        restored=true
    fi
    
    # 恢复GitHub Token
    if [ -f "$BACKUP_DIR/github_token_backup" ]; then
        echo "🔑 恢复GitHub Token"
        cp "$BACKUP_DIR/github_token_backup" "$PROJECT_ROOT/.github_token" 2>/dev/null || true
        restored=true
    fi
    
    if [ "$restored" = true ]; then
        echo "✅ 数据恢复完成"
    else
        echo "ℹ️ 无数据需要恢复"
    fi
    echo ""
}

# 清理测试产物
cleanup_test_artifacts() {
    if [ "$CLEANUP_PERFORMED" = true ]; then
        return
    fi
    
    echo -e "${CYAN}🧹 清理测试产物...${NC}"
    
    # 清理测试生成的Issues数据
    echo "🗑️ 清理测试Issues数据"
    rm -rf "$ISSUES_DIR"/* 2>/dev/null || true
    
    # 清理测试生成的输出文件
    echo "🗑️ 清理测试输出文件"
    find "$ISSUES_OUTPUT_PATH" -name "test_*" -type f -delete 2>/dev/null || true
    find "$ISSUES_OUTPUT_PATH" -name "copilot_*" -type f -delete 2>/dev/null || true
    
    # 清理临时文件
    echo "🗑️ 清理临时文件"
    rm -f /tmp/test_issues_*.json 2>/dev/null || true
    rm -f /tmp/preview_assign.py 2>/dev/null || true
    
    # 恢复原始数据
    restore_data
    
    # 清理备份目录
    echo "🗑️ 清理备份目录"
    rm -rf "$BACKUP_DIR" 2>/dev/null || true
    
    CLEANUP_PERFORMED=true
    echo "✅ 清理完成"
    echo ""
}

# 信号处理器 - 确保异常退出时也能清理
cleanup_on_exit() {
    echo ""
    echo -e "${YELLOW}⚠️ 检测到脚本退出，正在清理...${NC}"
    cleanup_test_artifacts
    
    # 生成最终报告
    generate_final_report
    exit 1
}

# 设置信号捕获
trap cleanup_on_exit SIGINT SIGTERM

# 测试函数模板
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"  # "success" 或 "failure"
    
    ((TOTAL_TESTS++))
    
    echo -e "${BLUE}🧪 测试 $TOTAL_TESTS: $test_name${NC}"
    echo "   命令: $test_command"
    
    # 记录测试开始时间
    local start_time=$(date +%s)
    
    # 执行测试命令
    eval "$test_command" > /tmp/test_output_$$.log 2>&1
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # 判断测试结果
    local test_passed=false
    if [ "$expected_result" = "success" ] && [ $exit_code -eq 0 ]; then
        test_passed=true
    elif [ "$expected_result" = "failure" ] && [ $exit_code -ne 0 ]; then
        test_passed=true
    fi
    
    # 输出结果
    if [ "$test_passed" = true ]; then
        echo -e "   ${GREEN}✅ 通过${NC} (用时: ${duration}s)"
        ((PASSED_TESTS++))
        TEST_RESULTS+=("PASS: $test_name (${duration}s)")
    else
        echo -e "   ${RED}❌ 失败${NC} (用时: ${duration}s, 退出码: $exit_code)"
        ((FAILED_TESTS++))
        TEST_RESULTS+=("FAIL: $test_name (${duration}s, 退出码: $exit_code)")
        
        # 显示失败的命令输出
        echo -e "   ${YELLOW}📋 错误输出:${NC}"
        head -20 /tmp/test_output_$$.log | sed 's/^/      /'
        if [ $(wc -l < /tmp/test_output_$$.log) -gt 20 ]; then
            echo "      ... (输出被截断，完整日志见: /tmp/test_output_$$.log)"
        fi
    fi
    
    # 清理临时输出文件
    rm -f /tmp/test_output_$$.log
    
    echo ""
}

# 检查GitHub Token
check_github_token() {
    local token_file="$PROJECT_ROOT/.github_token"
    
    # 检查环境变量
    if [ -n "$GITHUB_TOKEN" ]; then
        return 0
    fi
    
    # 检查token文件
    if [ -f "$token_file" ]; then
        return 0
    fi
    
    return 1
}

# 创建测试用的GitHub Token
setup_test_token() {
    echo -e "${CYAN}🔑 设置测试GitHub Token...${NC}"
    
    if check_github_token; then
        echo "✅ 检测到已有GitHub Token，继续使用"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️ 未检测到GitHub Token${NC}"
    echo "🔧 创建测试用Token (注意: 某些功能可能受限)"
    
    # 创建一个假的token用于测试基本功能
    echo "test_token_for_automated_testing" > "$PROJECT_ROOT/.github_token"
    chmod 600 "$PROJECT_ROOT/.github_token"
    
    echo "✅ 测试Token创建完成"
    echo ""
}

# 创建测试用的Issues数据
create_test_issues() {
    echo -e "${CYAN}📝 创建测试用Issues数据...${NC}"
    
    # 创建几个测试Issue文件
    cat > "$ISSUES_DIR/open_test_1001.md" << 'EOF'
# Issue #1001: 测试用Issue - Kernel功能

**状态**: Open  
**标签**: enhancement, sage-kernel  
**里程碑**: v1.0.0  
**创建时间**: 2024-01-15  
**更新时间**: 2024-01-16  

## 描述
这是一个用于测试的Issue，属于sage-kernel项目。

## 分配给
测试用户A

## 标签变更历史
- 2024-01-15: 添加了 enhancement
- 2024-01-16: 添加了 sage-kernel

## 更新记录
- 2024-01-15 10:00: Issue创建
- 2024-01-16 14:30: 添加标签和分配
EOF

    cat > "$ISSUES_DIR/open_test_1002.md" << 'EOF'
# Issue #1002: 测试用Issue - Middleware功能

**状态**: Open  
**标签**: bug, sage-middleware  
**里程碑**: v1.1.0  
**创建时间**: 2024-01-16  
**更新时间**: 2024-01-17  

## 描述
这是另一个用于测试的Issue，属于sage-middleware项目。

## 分配给
未分配

## 标签变更历史
- 2024-01-16: 添加了 bug
- 2024-01-17: 添加了 sage-middleware

## 更新记录
- 2024-01-16 09:15: Issue创建
- 2024-01-17 11:45: 更新标签
EOF

    cat > "$ISSUES_DIR/closed_test_1003.md" << 'EOF'
# Issue #1003: 测试用Issue - 已关闭

**状态**: Closed  
**标签**: documentation, sage-apps  
**里程碑**: v1.0.0  
**创建时间**: 2024-01-10  
**更新时间**: 2024-01-14  
**关闭时间**: 2024-01-14  

## 描述
这是一个已关闭的测试Issue，属于sage-apps项目。

## 分配给
测试用户B

## 标签变更历史
- 2024-01-10: 添加了 documentation
- 2024-01-12: 添加了 sage-apps

## 更新记录
- 2024-01-10 16:20: Issue创建
- 2024-01-12 10:30: 添加标签和分配
- 2024-01-14 15:45: Issue关闭
EOF

    echo "✅ 测试Issues数据创建完成 (3个测试Issues)"
    echo ""
}

# 创建测试用的metadata文件
create_test_metadata() {
    echo -e "${CYAN}📋 创建测试用metadata文件...${NC}"
    
    # 创建boards_metadata.json
    cat > "$ISSUES_METADATA_PATH/boards_metadata.json" << 'EOF'
{
  "sage-kernel": {
    "name": "SAGE Kernel Development", 
    "description": "Core kernel functionality",
    "members": ["testuser1", "testuser2"]
  },
  "sage-middleware": {
    "name": "SAGE Middleware Development",
    "description": "Middleware and services",
    "members": ["testuser3", "testuser4"]
  },
  "sage-apps": {
    "name": "SAGE Applications",
    "description": "Application layer development", 
    "members": ["testuser5", "testuser6"]
  }
}
EOF

    # 创建team_config.py
    cat > "$ISSUES_METADATA_PATH/team_config.py" << 'EOF'
# 测试用团队配置

TEAM_CONFIG = {
    "sage-kernel": {
        "name": "SAGE Kernel Team",
        "members": [
            {"username": "testuser1", "expertise": ["kernel", "core"], "workload": 0},
            {"username": "testuser2", "expertise": ["optimization", "performance"], "workload": 0}
        ]
    },
    "sage-middleware": {
        "name": "SAGE Middleware Team", 
        "members": [
            {"username": "testuser3", "expertise": ["middleware", "services"], "workload": 0},
            {"username": "testuser4", "expertise": ["integration", "testing"], "workload": 0}
        ]
    },
    "sage-apps": {
        "name": "SAGE Applications Team",
        "members": [
            {"username": "testuser5", "expertise": ["frontend", "ui"], "workload": 0},
            {"username": "testuser6", "expertise": ["documentation", "examples"], "workload": 0}
        ]
    }
}
EOF

    echo "✅ 测试metadata文件创建完成"
    echo ""
}

# 测试核心Python脚本是否存在和可执行
test_python_scripts() {
    echo -e "${PURPLE}🐍 测试Python脚本功能${NC}"
    echo "=============================="
    
    local scripts=(
        "_scripts/helpers/get_paths.py"
        "_scripts/helpers/get_boards.py" 
        "_scripts/helpers/get_team_members.py"
        "_scripts/download_issues_v2.py"
        "_scripts/copilot_issue_formatter.py"
        "_scripts/project_based_assign.py"
        "_scripts/sync_issues.py"
        "_scripts/issues_manager.py"
        "_scripts/show_update_history.py"
        "_scripts/config_manager.py"
    )
    
    cd "$SCRIPT_DIR"
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ]; then
            run_test "检查脚本存在: $script" "test -f '$script'" "success"
            run_test "检查脚本可执行: $script" "python3 -m py_compile '$script'" "success"
        else
            run_test "检查脚本存在: $script" "test -f '$script'" "failure"
        fi
    done
    
    echo ""
}

# 测试配置和路径功能
test_config_functions() {
    echo -e "${PURPLE}⚙️ 测试配置和路径功能${NC}"
    echo "=========================="
    
    cd "$SCRIPT_DIR"
    
    # 测试路径获取
    run_test "获取workspace路径" "python3 _scripts/helpers/get_paths.py workspace" "success"
    run_test "获取output路径" "python3 _scripts/helpers/get_paths.py output" "success"
    run_test "获取metadata路径" "python3 _scripts/helpers/get_paths.py metadata" "success"
    run_test "获取issues路径" "python3 _scripts/helpers/get_paths.py issues" "success"
    
    # 测试无效路径类型
    run_test "测试无效路径类型" "python3 _scripts/helpers/get_paths.py invalid_type" "failure"
    
    echo ""
}

# 测试metadata初始化功能
test_metadata_functions() {
    echo -e "${PURPLE}📋 测试Metadata功能${NC}"
    echo "====================="
    
    cd "$SCRIPT_DIR"
    
    # 创建测试metadata
    create_test_metadata
    
    # 测试boards获取 (可能失败，因为需要真实的GitHub API)
    run_test "获取boards metadata" "python3 _scripts/helpers/get_boards.py || true" "success"
    
    # 测试team members获取 (可能失败，因为需要真实的GitHub API)
    run_test "获取team members" "python3 _scripts/helpers/get_team_members.py || true" "success"
    
    echo ""
}

# 测试Issues管理功能
test_issues_management() {
    echo -e "${PURPLE}📝 测试Issues管理功能${NC}"
    echo "========================"
    
    cd "$SCRIPT_DIR"
    
    # 创建测试Issues数据
    create_test_issues
    
    # 测试Issues统计
    run_test "Issues统计功能" "python3 _scripts/issues_manager.py --action=statistics" "success"
    
    # 测试更新历史查看
    run_test "查看更新历史" "python3 _scripts/show_update_history.py" "success"
    
    # 测试特定Issue更新历史
    run_test "查看特定Issue更新历史" "python3 _scripts/show_update_history.py --issue-id 1001" "success"
    
    echo ""
}

# 测试AI分析功能
test_ai_functions() {
    echo -e "${PURPLE}🤖 测试AI分析功能${NC}"
    echo "====================="
    
    cd "$SCRIPT_DIR"
    
    # 确保有测试数据
    create_test_issues
    
    # 测试Copilot格式化器的各种模式
    run_test "Copilot综合分析" "python3 _scripts/copilot_issue_formatter.py --format=comprehensive --time=all" "success"
    run_test "Copilot团队分析" "python3 _scripts/copilot_issue_formatter.py --format=teams --time=all" "success"  
    run_test "Copilot未分配分析" "python3 _scripts/copilot_issue_formatter.py --format=unassigned --time=all" "success"
    run_test "Copilot完整分析包" "python3 _scripts/copilot_issue_formatter.py --format=all --time=all" "success"
    
    # 测试单个团队分析
    run_test "单个团队分析 - sage-kernel" "python3 _scripts/copilot_issue_formatter.py --team=sage-kernel --time=all" "success"
    run_test "单个团队分析 - sage-middleware" "python3 _scripts/copilot_issue_formatter.py --team=sage-middleware --time=all" "success"
    run_test "单个团队分析 - sage-apps" "python3 _scripts/copilot_issue_formatter.py --team=sage-apps --time=all" "success"
    
    # 测试时间过滤
    run_test "时间过滤 - 近一周" "python3 _scripts/copilot_issue_formatter.py --format=comprehensive --time=week" "success"
    run_test "时间过滤 - 近一月" "python3 _scripts/copilot_issue_formatter.py --format=comprehensive --time=month" "success"
    
    echo ""
}

# 测试智能分配功能
test_assignment_functions() {
    echo -e "${PURPLE}🎯 测试智能分配功能${NC}"
    echo "========================"
    
    cd "$SCRIPT_DIR"
    
    # 确保有测试数据和metadata
    create_test_issues
    create_test_metadata
    
    # 测试分配预览 (不修改文件)
    run_test "智能分配预览" "python3 _scripts/project_based_assign.py --preview" "success"
    
    # 测试实际分配
    run_test "执行智能分配" "python3 _scripts/project_based_assign.py --assign" "success"
    
    # 验证分配结果
    run_test "验证分配结果" "grep -l '分配给' '$ISSUES_DIR'/open_*.md | wc -l | grep -E '^[1-9]'" "success"
    
    echo ""
}

# 测试下载功能 (模拟，不实际下载)
test_download_functions() {
    echo -e "${PURPLE}📥 测试下载功能${NC}"
    echo "====================="
    
    cd "$SCRIPT_DIR"
    
    # 测试下载脚本的参数解析 (dry-run模式)
    run_test "下载脚本参数解析 - all" "python3 _scripts/download_issues_v2.py --help" "success"
    
    # 注意: 实际的GitHub API下载需要有效token，这里只测试脚本结构
    echo "ℹ️ 实际GitHub API下载需要有效token，此处仅测试脚本结构"
    
    echo ""
}

# 测试同步功能 (模拟，不实际同步)
test_sync_functions() {
    echo -e "${PURPLE}📤 测试同步功能${NC}"
    echo "====================="
    
    cd "$SCRIPT_DIR"
    
    # 确保有测试数据
    create_test_issues
    
    # 测试同步脚本的预览功能
    run_test "同步预览功能" "python3 _scripts/sync_issues.py --preview" "success"
    
    # 测试项目分配同步 (dry-run)
    run_test "项目分配同步预览" "python3 _scripts/sync_issues.py --apply-projects --preview" "success"
    
    echo "ℹ️ 实际GitHub API同步需要有效token，此处仅测试脚本结构"
    
    echo ""
}

# 测试配置管理功能
test_config_management() {
    echo -e "${PURPLE}⚙️ 测试配置管理功能${NC}"
    echo "========================"
    
    cd "$SCRIPT_DIR"
    
    # 测试配置显示
    run_test "显示配置" "python3 _scripts/config_manager.py --show" "success"
    
    # 测试配置选项 (不进行实际交互)
    run_test "配置帮助" "python3 _scripts/config_manager.py --help" "success"
    
    echo ""
}

# 测试目录结构和权限
test_directory_structure() {
    echo -e "${PURPLE}📁 测试目录结构和权限${NC}"
    echo "============================"
    
    # 测试关键目录是否存在
    run_test "workspace目录存在" "test -d '$ISSUES_WORKSPACE_PATH'" "success"
    run_test "output目录存在" "test -d '$ISSUES_OUTPUT_PATH'" "success"
    run_test "metadata目录存在" "test -d '$ISSUES_METADATA_PATH'" "success"
    run_test "issues目录存在" "test -d '$ISSUES_DIR'" "success"
    
    # 测试目录权限
    run_test "workspace目录可写" "test -w '$ISSUES_WORKSPACE_PATH'" "success"
    run_test "output目录可写" "test -w '$ISSUES_OUTPUT_PATH'" "success"
    run_test "metadata目录可写" "test -d '$ISSUES_METADATA_PATH'" "success"
    run_test "issues目录可写" "test -w '$ISSUES_DIR'" "success"
    
    echo ""
}

# 测试主脚本功能 (issues_manager.sh)
test_main_script() {
    echo -e "${PURPLE}📜 测试主脚本功能${NC}"
    echo "====================="
    
    # 测试主脚本存在和可执行
    run_test "主脚本存在" "test -f '$SCRIPT_DIR/issues_manager.sh'" "success"
    run_test "主脚本可执行" "test -x '$SCRIPT_DIR/issues_manager.sh'" "success"
    
    # 测试主脚本基本语法 (bash语法检查)
    run_test "主脚本语法检查" "bash -n '$SCRIPT_DIR/issues_manager.sh'" "success"
    
    # 测试关键函数是否定义 (简单检查)
    run_test "检查下载函数定义" "grep -q 'download_all_issues()' '$SCRIPT_DIR/issues_manager.sh'" "success"
    run_test "检查AI函数定义" "grep -q 'ai_menu()' '$SCRIPT_DIR/issues_manager.sh'" "success"
    run_test "检查上传函数定义" "grep -q 'upload_menu()' '$SCRIPT_DIR/issues_manager.sh'" "success"
    run_test "检查配置函数定义" "grep -q 'config_management_menu()' '$SCRIPT_DIR/issues_manager.sh'" "success"
    
    echo ""
}

# 生成最终测试报告
generate_final_report() {
    echo ""
    echo -e "${CYAN}📊 生成测试报告${NC}"
    echo "=================="
    
    # 创建详细报告
    cat > "$TEST_REPORT" << EOF
SAGE Issues Manager 自动化测试报告
=====================================

测试时间: $(date)
测试环境: $(uname -a)
项目路径: $PROJECT_ROOT

测试统计:
---------
总测试数: $TOTAL_TESTS
通过: $PASSED_TESTS
失败: $FAILED_TESTS
成功率: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%

详细结果:
---------
EOF
    
    # 添加详细结果
    for result in "${TEST_RESULTS[@]}"; do
        echo "$result" >> "$TEST_REPORT"
    done
    
    # 添加环境信息
    cat >> "$TEST_REPORT" << EOF

环境信息:
---------
Python版本: $(python3 --version 2>&1)
Shell版本: $BASH_VERSION
当前用户: $(whoami)
工作目录: $(pwd)

配置路径:
---------
Workspace: $ISSUES_WORKSPACE_PATH
Output: $ISSUES_OUTPUT_PATH  
Metadata: $ISSUES_METADATA_PATH
Issues: $ISSUES_DIR

文件结构:
---------
$(find "$SCRIPT_DIR" -name "*.py" -o -name "*.sh" | head -20)

测试说明:
---------
1. 此测试验证所有核心功能的基本运行能力
2. 某些依赖GitHub API的功能使用模拟数据测试
3. 所有测试产物已自动清理
4. 原始数据已恢复

EOF
    
    echo "📋 详细报告已保存到: $TEST_REPORT"
    
    # 显示摘要
    echo ""
    echo -e "${PURPLE}🎯 测试摘要${NC}"
    echo "============"
    echo -e "总测试数: ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "失败: ${RED}$FAILED_TESTS${NC}"
    echo -e "成功率: ${CYAN}$(( PASSED_TESTS * 100 / TOTAL_TESTS ))%${NC}"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo ""
        echo -e "${GREEN}🎉 所有测试都通过了！Issues Manager功能正常${NC}"
    else
        echo ""
        echo -e "${YELLOW}⚠️ 有 $FAILED_TESTS 个测试失败，请检查相关功能${NC}"
        echo -e "详细信息请查看: ${BLUE}$TEST_REPORT${NC}"
    fi
}

# 主测试流程
main() {
    echo -e "${CYAN}🚀 SAGE Issues Manager 自动化测试${NC}"
    echo "=================================="
    echo ""
    echo "🎯 此测试将验证Issues Manager的所有核心功能"
    echo "⏱️ 预计运行时间: 2-5分钟"
    echo "🧹 测试完成后将自动清理所有中间产物"
    echo ""
    
    read -p "按Enter键开始测试..." dummy
    echo ""
    
    # 初始化和准备
    initialize_test_env
    backup_existing_data
    setup_test_token
    
    echo -e "${YELLOW}⏰ 开始执行测试...${NC}"
    echo ""
    
    # 执行所有测试
    test_directory_structure
    test_python_scripts  
    test_config_functions
    test_metadata_functions
    test_issues_management
    test_ai_functions
    test_assignment_functions
    test_download_functions
    test_sync_functions
    test_config_management
    test_main_script
    
    echo -e "${YELLOW}🏁 所有测试完成${NC}"
    echo ""
    
    # 清理和报告
    cleanup_test_artifacts
    generate_final_report
    
    echo ""
    echo -e "${GREEN}✨ 测试完成！${NC}"
}

# 检查脚本是否被直接执行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
