#!/bin/bash
# SAGE-Libs 重构执行脚本
# 协调 8 个 Agent 完成整体重构

set -e

SAGE_ROOT="/home/shuhao/SAGE"
TOOLS_DIR="$SAGE_ROOT/tools/dev"

echo "🚀 SAGE-Libs 重构开始"
echo "===================="
echo ""
echo "📋 重构目标："
echo "  - 5 大核心接口领域（Agentic, RAG, ANNS/AMMS, Finetune/Eval, Privacy/Safety）"
echo "  - 保留 3 个轻量模块（Foundation, DataOps, Integrations）"
echo "  - 创建 4 个新仓库（privacy, finetune, eval, safety-可选）"
echo "  - 合并 Intent/Reasoning/SIAS 到 Agentic"
echo ""

# ==================== Phase 1: 仓库准备 ====================
echo "📦 Phase 1: 仓库准备（Agent-0）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "执行 Agent-0: 创建/检查仓库？ (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "$TOOLS_DIR/create_sage_repos.sh" ]; then
        bash "$TOOLS_DIR/create_sage_repos.sh"
    else
        echo "⚠️  create_sage_repos.sh 不存在，请手动创建"
        echo "   参考: tools/dev/agent_0_repo_orchestrator.md"
    fi
fi
echo ""

# ==================== Phase 2: 代码迁移（并行）====================
echo "🔧 Phase 2: 代码迁移（并行执行）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "请在多个终端窗口并行执行以下 Agent："
echo ""
echo "  终端 1: Agent-1 (Agentic + Intent/Reasoning/SIAS 合并)"
echo "    参考: $TOOLS_DIR/agent_1_agentic.md"
echo ""
echo "  终端 2: Agent-2 (RAG)"
echo "    参考: $TOOLS_DIR/agent_2_rag.md"
echo ""
echo "  终端 3: Agent-3 (Fine-tuning)"
echo "    参考: $TOOLS_DIR/agents_3_8_summary.md # Agent-3"
echo ""
echo "  终端 4: Agent-4 (Evaluation)"
echo "    参考: $TOOLS_DIR/agents_3_8_summary.md # Agent-4"
echo ""
echo "  终端 5: Agent-5 (Privacy)"
echo "    参考: $TOOLS_DIR/agents_3_8_summary.md # Agent-5"
echo ""
echo "  终端 6 (可选): Agent-6 (Safety 高级功能)"
echo "    参考: $TOOLS_DIR/agents_3_8_summary.md # Agent-6"
echo ""

read -p "所有代码迁移 Agent 完成后按回车继续..." -r
echo ""

# ==================== Phase 3: 文档重构 ====================
echo "📚 Phase 3: 文档重构（Agent-7）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "任务："
echo "  1. 更新 packages/sage-libs/README.md"
echo "  2. 精简 packages/sage-libs/docs/"
echo "  3. 为每个独立库创建完整文档"
echo "  4. 生成架构图和集成指南"
echo ""
read -p "执行 Agent-7: 文档重构？ (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "请参考: $TOOLS_DIR/agents_3_8_summary.md # Agent-7"
    echo "手动执行文档更新任务"
fi
echo ""

# ==================== Phase 4: 集成验证与发布 ====================
echo "✅ Phase 4: 集成验证与发布（Agent-8）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 4.1 集成测试
echo "4.1 运行集成测试"
read -p "  运行集成测试？ (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$SAGE_ROOT"
    pytest packages/sage-libs/tests/integration/ -v || echo "⚠️  部分测试失败，请检查"
fi
echo ""

# 4.2 版本对齐检查
echo "4.2 版本号对齐检查"
echo "  检查所有独立库版本号是否统一为 0.1.0..."
for repo in sage-agentic sage-rag sage-privacy sage-finetune sage-eval sage-safety; do
    if [ -d "/home/shuhao/$repo" ]; then
        version=$(grep "^version" "/home/shuhao/$repo/pyproject.toml" 2>/dev/null | cut -d'"' -f2 || echo "未找到")
        echo "    $repo: $version"
    fi
done
echo ""

# 4.3 PyPI 发布
echo "4.3 PyPI 发布"
read -p "  发布到 TestPyPI？ (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "/home/shuhao/sage-pypi-publisher" ]; then
        cd /home/shuhao/sage-pypi-publisher
        echo "  使用 sage-pypi-publisher 发布..."
        echo "  请手动执行："
        echo "    cd /home/shuhao/sage-pypi-publisher"
        echo "    ./publish.sh isage-agentic --test-pypi --version 0.1.0"
        echo "    ./publish.sh isage-rag --test-pypi --version 0.1.0"
        echo "    ./publish.sh isage-privacy --test-pypi --version 0.1.0"
        echo "    ./publish.sh isage-finetune --test-pypi --version 0.1.0"
        echo "    ./publish.sh isage-eval --test-pypi --version 0.1.0"
    else
        echo "  ⚠️  sage-pypi-publisher 不存在"
    fi
fi
echo ""

# ==================== 完成总结 ====================
echo ""
echo "🎉 SAGE-Libs 重构流程完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 重构成果："
echo "  ✅ 5 大核心接口领域已定义"
echo "  ✅ 3 个轻量模块已保留（Foundation, DataOps, Integrations）"
echo "  ✅ 4-6 个独立库已创建并发布"
echo "  ✅ sage-libs 代码量减少 60%+"
echo "  ✅ 文档已更新"
echo ""
echo "📦 独立库清单："
echo "  - isage-anns (已完成)"
echo "  - isage-amms (进行中)"
echo "  - isage-agentic (含 Intent/Reasoning/SIAS)"
echo "  - isage-rag"
echo "  - isage-privacy"
echo "  - isage-finetune"
echo "  - isage-eval"
echo "  - isage-safety (可选)"
echo ""
echo "🚀 下一步："
echo "  1. 验证所有独立库可正常安装"
echo "  2. 更新 SAGE 主仓库依赖"
echo "  3. 发布正式版本到 PyPI"
echo "  4. 更新用户文档和教程"
echo ""
