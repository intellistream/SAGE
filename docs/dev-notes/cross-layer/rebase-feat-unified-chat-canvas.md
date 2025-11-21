# feat/unified-chat-canvas Rebase 总结

## 执行策略

由于 `feat/unified-chat-canvas` 分支与 `main-dev` 存在大量冲突（139个提交需要 rebase，80+ 个文件冲突），采用了 **cherry-pick
策略**提取核心功能。

## 操作步骤

1. **创建新分支**: `feat/unified-chat-canvas-rebased` (基于 `main-dev`)
1. **Cherry-pick 核心提交**: 提取 `602daab3` - "feat(studio): unified Chat + Canvas dual-mode interface
   with RAG Pipeline"
1. **解决冲突**:
   - Submodule (data): 使用 main-dev 版本
   - sage-gateway (新包): 使用 feat 分支版本
   - 前端代码 (App.tsx, Toolbar.tsx, ChatMode.tsx 等): 使用 feat 分支版本
   - package.json: 合并两边的依赖

## 核心功能保留

### ✅ sage-gateway 包 (新增)

- OpenAI 兼容 API
- RAG Pipeline: 文档爬取 → ChromaDB → QA 生成
- Session 管理与 NeuroMem 存储
- `/v1/chat/completions` 接口

### ✅ sage-studio 双模式 UI

- **Chat 模式**: 对话界面 + RAG 后端
- **Canvas 模式**: 可视化 Pipeline 构建器（原 Builder）
- 工具栏模式切换
- Markdown 消息渲染

### ✅ sage-cli 增强

- 自动启动 gateway 服务 (端口 8000)
- 改进的错误处理和日志

### ✅ Pipeline Builder 修复

- 智能 API key 检测 (Qwen/GPT)
- 环境变量加载 (~/.sage/.env.json)
- 增强的 operator 配置与默认值
- 节点类型转换修复

## 文件变更统计

```
19 files changed, 922 insertions(+), 345 deletions(-)
```

主要变更文件:

- packages/sage-gateway/\* (新包)
- packages/sage-studio/src/sage/studio/frontend/\*
- packages/sage-studio/src/sage/studio/config/backend/api.py
- packages/sage-studio/src/sage/studio/chat_manager.py
- packages/sage-middleware/src/sage/middleware/operators/rag/generator.py
- tools/install/installation_table/\*

## 下一步建议

1. **测试验证**: 运行 `sage-dev project test` 确保没有破坏现有功能
1. **功能测试**: 启动 sage-studio 验证 Chat 和 Canvas 模式切换（见下方启动步骤）
1. **推送分支**: `git push origin feat/unified-chat-canvas-rebased`
1. **创建 PR**: 将 `feat/unified-chat-canvas-rebased` merge 到 `main-dev`
1. **清理**: 删除旧的 `feat/unified-chat-canvas` 分支（如果需要）

## 如何启动和使用

### 首次启动（完整步骤）

```bash
# 1. 构建 Studio 前端（仅首次需要）
sage studio build

# 2. 启动 Gateway 服务（在新终端窗口）
sage-gateway --host 0.0.0.0 --port 8000

# 3. 启动 Studio 服务（在另一个终端窗口）
sage studio start --host 0.0.0.0

# 4. 在浏览器中访问
# Studio 默认地址: http://localhost:5173 (dev模式) 或 http://localhost:3000 (prod模式)
```

### 后续启动（跳过 build）

```bash
# 终端 1: 启动 Gateway
sage-gateway --host 0.0.0.0 --port 8000

# 终端 2: 启动 Studio
sage studio start --host 0.0.0.0
```

### 使用双模式 UI

1. **Canvas 模式**（可视化 Pipeline 构建）:
   - 拖拽节点创建 Pipeline
   - 配置操作符参数
   - 可视化执行流程

2. **Chat 模式**（对话界面 + RAG）:
   - 点击工具栏切换到 Chat 模式
   - 与 Gateway 后端的 RAG Pipeline 对话
   - 支持 Markdown 渲染和数学公式

### 配置要求

- Gateway 依赖：需要安装 `isage-gateway` 包
- 环境变量：配置 `~/.sage/.env.json` 包含 API keys（用于 LLM 调用）
- 前端依赖：首次需要运行 `sage studio build` 安装 npm 依赖

## 命令参考

```bash
# 当前分支
git branch
# -> feat/unified-chat-canvas-rebased

# 查看提交
git log --oneline -1
# -> 239af97b feat(studio): unified Chat + Canvas dual-mode interface with RAG Pipeline

# 推送到远程
git push origin feat/unified-chat-canvas-rebased

# 创建 PR (通过 GitHub Web UI 或 gh CLI)
gh pr create --base main-dev --head feat/unified-chat-canvas-rebased \
  --title "feat(studio): unified Chat + Canvas dual-mode interface with RAG Pipeline" \
  --body "Cherry-picked from feat/unified-chat-canvas, resolves conflicts with main-dev"
```

## 冲突解决详情

### Submodule 冲突

- `packages/sage-benchmark/src/sage/data`: 使用 main-dev 的版本，保持与当前开发分支一致

### 新增包冲突 (add/add)

- `packages/sage-gateway/*`: 完全来自 feat/unified-chat-canvas，这是新功能包
- `packages/sage-studio/src/sage/studio/chat_manager.py`: 新文件，来自 feat 分支
- `packages/sage-studio/src/sage/studio/frontend/src/components/ChatMode.tsx`: 新组件

### 代码合并冲突

- `packages/sage-studio/src/sage/studio/frontend/package.json`: 合并了两边的依赖 (rehype-katex, remark-math)
- `packages/sage-studio/src/sage/studio/frontend/package-lock.json`: 使用 feat 分支版本，包含新依赖
- `packages/sage-studio/src/sage/studio/frontend/src/App.tsx`: 使用 feat 分支版本，支持 Chat/Canvas 双模式
- `packages/sage-studio/src/sage/studio/frontend/src/components/Toolbar.tsx`: 使用 feat 分支版本，添加模式切换
- `packages/sage-studio/src/sage/studio/frontend/src/services/api.ts`: 使用 feat 分支版本，新增 Chat API
