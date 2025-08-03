#!/bin/bash

# GitHub Actions 本地测试菜单
# 提供多种测试选项

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║             GitHub Actions 本地测试工具                  ║"
echo "║                  SAGE 项目专用                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

show_menu() {
    echo -e "${CYAN}请选择测试方式:${NC}"
    echo ""
    echo -e "${GREEN}1.${NC} 🚀 完整本地模拟测试 (推荐)"
    echo -e "${GREEN}2.${NC} 🐳 Act + Docker 测试"
    echo -e "${GREEN}3.${NC} 📋 查看工作流作业列表"
    echo -e "${GREEN}4.${NC} 🧪 测试特定作业"
    echo -e "${GREEN}5.${NC} 📊 查看测试报告"
    echo -e "${GREEN}6.${NC} 🛠️  检查环境状态"
    echo -e "${GREEN}7.${NC} 📝 生成工作流文档"
    echo -e "${RED}0.${NC} 退出"
    echo ""
    echo -e "${YELLOW}请输入选项 (0-7):${NC} "
}

check_dependencies() {
    echo -e "${BLUE}🔍 检查依赖工具...${NC}"
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        echo -e "${GREEN}✅ Python3: $(python3 --version)${NC}"
    else
        echo -e "${RED}❌ Python3 未安装${NC}"
    fi
    
    # 检查 act
    if command -v act &> /dev/null; then
        echo -e "${GREEN}✅ Act: $(act --version 2>&1 | head -1)${NC}"
    else
        echo -e "${YELLOW}⚠️  Act 未安装${NC}"
    fi
    
    # 检查 Docker
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            echo -e "${GREEN}✅ Docker: 运行中${NC}"
        else
            echo -e "${YELLOW}⚠️  Docker: 已安装但未运行${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Docker 未安装${NC}"
    fi
    
    # 检查工作流文件
    if [ -f ".github/workflows/build-release.yml" ]; then
        echo -e "${GREEN}✅ 工作流文件: build-release.yml${NC}"
    else
        echo -e "${RED}❌ 工作流文件未找到${NC}"
    fi
    
    echo ""
}

run_local_simulation() {
    echo -e "${BLUE}🚀 运行完整本地模拟测试...${NC}"
    echo ""
    
    if [ -f "test_github_actions.sh" ]; then
        chmod +x test_github_actions.sh
        ./test_github_actions.sh
    else
        echo -e "${RED}❌ 本地测试脚本未找到${NC}"
    fi
}

run_act_test() {
    echo -e "${BLUE}🐳 运行 Act + Docker 测试...${NC}"
    echo ""
    
    if command -v act &> /dev/null; then
        if [ -f "test_act_local.sh" ]; then
            chmod +x test_act_local.sh
            ./test_act_local.sh
        else
            echo "直接运行 act 命令..."
            act -W .github/workflows/build-release.yml --list
        fi
    else
        echo -e "${RED}❌ Act 工具未安装${NC}"
        echo -e "${YELLOW}请访问 https://github.com/nektos/act 安装${NC}"
    fi
}

list_workflow_jobs() {
    echo -e "${BLUE}📋 查看工作流作业列表...${NC}"
    echo ""
    
    if command -v act &> /dev/null; then
        act -W .github/workflows/build-release.yml --list
    else
        echo -e "${YELLOW}使用 grep 分析工作流文件...${NC}"
        if [ -f ".github/workflows/build-release.yml" ]; then
            echo "发现的作业:"
            grep -n "jobs:" -A 20 .github/workflows/build-release.yml | grep -E "^\s*[a-zA-Z_]+:" | head -10
        else
            echo -e "${RED}工作流文件未找到${NC}"
        fi
    fi
}

test_specific_job() {
    echo -e "${BLUE}🧪 测试特定作业...${NC}"
    echo ""
    echo "可用的作业:"
    echo "1. build (构建)"
    echo "2. test (测试)"
    echo "3. release (发布)"
    echo "4. cleanup (清理)"
    echo ""
    echo -e "${YELLOW}请输入作业名称 (如: build):${NC} "
    read job_name
    
    if [ -n "$job_name" ]; then
        if command -v act &> /dev/null; then
            echo -e "${BLUE}测试作业: $job_name${NC}"
            act -W .github/workflows/build-release.yml --job "$job_name" --dryrun
        else
            echo -e "${RED}❌ Act 工具未安装${NC}"
        fi
    else
        echo -e "${RED}❌ 未输入作业名称${NC}"
    fi
}

show_test_report() {
    echo -e "${BLUE}📊 查看测试报告...${NC}"
    echo ""
    
    if [ -f "act_test_report.md" ]; then
        if command -v cat &> /dev/null; then
            cat act_test_report.md
        fi
    else
        echo -e "${RED}❌ 测试报告未找到${NC}"
        echo -e "${YELLOW}请先运行测试生成报告${NC}"
    fi
}

generate_workflow_docs() {
    echo -e "${BLUE}📝 生成工作流文档...${NC}"
    echo ""
    
    cat > workflow_docs.md << 'EOF'
# GitHub Actions 工作流文档

## build-release.yml 工作流

### 触发条件
- Push 到 main 分支
- 创建以 'v' 开头的标签
- 发布 Release

### 作业流程

#### 1. build (构建作业)
- **运行环境**: ubuntu-latest
- **依赖**: 无
- **主要步骤**:
  - 检出代码
  - 设置 Python 3.11
  - 安装构建依赖
  - 获取版本信息
  - 构建 C 扩展
  - 构建 Python 包
  - 验证包内容
  - 测试包安装

#### 2. test (测试作业)
- **运行环境**: ubuntu-latest
- **依赖**: build 作业完成
- **矩阵策略**: Python 3.9, 3.10, 3.11
- **主要步骤**:
  - 下载构建产物
  - 安装并测试包

#### 3. release (发布作业)
- **运行环境**: ubuntu-latest
- **依赖**: build, test 作业完成
- **触发条件**: 仅在标签推送时
- **主要步骤**:
  - 创建 GitHub Release
  - 上传构建产物
  - 发布到私有仓库

#### 4. cleanup (清理作业)
- **运行环境**: ubuntu-latest
- **依赖**: 所有作业完成后
- **触发条件**: 总是执行
- **主要步骤**:
  - 清理超过30天的构建产物

### 环境变量
- `PYTHON_VERSION`: 3.11
- `GITHUB_TOKEN`: GitHub 访问令牌
- `PRIVATE_REGISTRY_URL`: 私有仓库地址
- `PRIVATE_REGISTRY_TOKEN`: 私有仓库令牌

### 输出产物
- Python wheel 包 (.whl)
- 源码分发包 (.tar.gz)
- 字节码包 (如果存在)

EOF

    echo -e "${GREEN}✅ 工作流文档已生成: workflow_docs.md${NC}"
}

# 主循环
while true; do
    show_menu
    read -r choice
    
    case $choice in
        1)
            echo ""
            run_local_simulation
            echo ""
            echo -e "${GREEN}按任意键继续...${NC}"
            read -n 1
            ;;
        2)
            echo ""
            run_act_test
            echo ""
            echo -e "${GREEN}按任意键继续...${NC}"
            read -n 1
            ;;
        3)
            echo ""
            list_workflow_jobs
            echo ""
            echo -e "${GREEN}按任意键继续...${NC}"
            read -n 1
            ;;
        4)
            echo ""
            test_specific_job
            echo ""
            echo -e "${GREEN}按任意键继续...${NC}"
            read -n 1
            ;;
        5)
            echo ""
            show_test_report
            echo ""
            echo -e "${GREEN}按任意键继续...${NC}"
            read -n 1
            ;;
        6)
            echo ""
            check_dependencies
            echo -e "${GREEN}按任意键继续...${NC}"
            read -n 1
            ;;
        7)
            echo ""
            generate_workflow_docs
            echo ""
            echo -e "${GREEN}按任意键继续...${NC}"
            read -n 1
            ;;
        0)
            echo -e "${GREEN}再见! 👋${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选项，请输入 0-7${NC}"
            echo -e "${GREEN}按任意键继续...${NC}"
            read -n 1
            ;;
    esac
    
    clear
done
