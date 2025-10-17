# 📚 SAGE Studio v2.0 - 文档导航

> **当前状态**: Phase 2 完成 (100%) ✅ | Phase 3 进行中 (15%) 🔄  
> **最后更新**: 2025-10-17

---

## 🚀 快速开始

### 5分钟上手

```bash
# 1. 启动后端
cd /home/chaotic/SAGE/packages/sage-studio
python -m sage.studio.config.backend.api &

# 2. 启动前端
cd frontend-v2
npm run dev

# 3. 访问
# 前端: http://localhost:3000
# API文档: http://localhost:8080/docs
```

**必读**: [README.md](./README.md) | [QUICK_ACCESS.md](./QUICK_ACCESS.md)

---

## 📂 文档结构

### 🎯 核心文档

| 文档 | 说明 | 优先级 |
|------|------|--------|
| [README.md](./README.md) | 项目主页，完整指南 | ⭐⭐⭐⭐⭐ |
| [QUICK_ACCESS.md](./QUICK_ACCESS.md) | 快速访问入口，常用命令 | ⭐⭐⭐⭐⭐ |
| [CHANGELOG.md](./CHANGELOG.md) | 包版本更新日志 | ⭐⭐⭐ |

### 🎨 前端文档 (React v2)

| 文档 | 说明 | 状态 |
|------|------|------|
| [frontend-v2/README.md](./frontend-v2/README.md) | React 前端详细说明 | ⭐⭐⭐⭐⭐ |
| [frontend-v2/CHANGELOG.md](./frontend-v2/CHANGELOG.md) | 前端更新日志 | ⭐⭐⭐⭐ |
| [PHASE2_FINAL_COMPLETION_REPORT.md](./frontend-v2/PHASE2_FINAL_COMPLETION_REPORT.md) | Phase 2 完成报告 | ⭐⭐⭐⭐ |
| [FIX_UNDO_REDO_BUG_REPORT.md](./frontend-v2/FIX_UNDO_REDO_BUG_REPORT.md) | 撤销/重做修复 | ⭐⭐⭐ |
| [UNDO_REDO_TEST_CHECKLIST.md](./frontend-v2/UNDO_REDO_TEST_CHECKLIST.md) | 测试清单 | ⭐⭐⭐ |

### 📋 战略规划

| 文档 | 说明 | 价值 |
|------|------|------|
| [COMPETITIVE_ANALYSIS.md](./COMPETITIVE_ANALYSIS.md) | vs LangFlow/Coze 竞品分析 | ⭐⭐⭐⭐⭐ |
| [COMPETITIVE_STRATEGY_QUICKREF.md](./COMPETITIVE_STRATEGY_QUICKREF.md) | 战略快速参考 | ⭐⭐⭐⭐⭐ |
| [PHASE3_PLAYGROUND_PLAN.md](./frontend-v2/PHASE3_PLAYGROUND_PLAN.md) | Phase 3 实施计划 | ⭐⭐⭐⭐⭐ |
| [docs/STUDIO_EVOLUTION_ROADMAP.md](./docs/STUDIO_EVOLUTION_ROADMAP.md) | 完整演进路线图 | ⭐⭐⭐⭐ |

### 🏛️ Phase 1 文档 (已完成)

| 文档 | 说明 | 备注 |
|------|------|------|
| [docs/standalone-mode/](./docs/standalone-mode/) | Phase 1 独立运行文档 | 保留作为参考 |
| [verify_standalone.py](./verify_standalone.py) | Phase 1 验证脚本 | 可用于测试 |

---

## 📊 进度总览

```
Phase 1: 接口抽象        ████████████████████ 100% ✅ (已完成)
Phase 2: 可视化编辑器    ████████████████████ 100% ✅ (已完成)
Phase 3: 追平体验        ███░░░░░░░░░░░░░░░░░  15% 🔄 (进行中)
Phase 4: RAG 专业化      ░░░░░░░░░░░░░░░░░░░░   0% 📋 (规划中)

总体进度: 54%
```

### ✅ 已完成 (Phase 1-2)

**Phase 1** (100%):
- 插件系统架构
- 节点定义和执行引擎
- FastAPI 后端 API
- 11/11 集成测试通过

**Phase 2** (100%):
- React Flow 可视化编辑器
- 流程保存/加载/运行/停止
- 动态节点配置表单
- 画布缩放控制
- **状态轮询** (实时更新) ✨
- **撤销/重做** (50步历史) ✨
- **键盘快捷键** (Ctrl+Z/Y/S, Delete) ✨
- Angular/React 格式兼容

### 🔄 进行中 (Phase 3)

**目标**: 追平 LangFlow 核心体验

- [x] 状态轮询、撤销/重做、键盘快捷键 ✅
- [ ] **Playground** (P0) - 交互式调试面板
- [ ] **Tweaks** (P1) - 运行时参数覆盖
- [ ] **模板库** (P1) - 10+ RAG 模板

**详见**: [PHASE3_PLAYGROUND_PLAN.md](./frontend-v2/PHASE3_PLAYGROUND_PLAN.md)

### 📋 规划中 (Phase 4)

**目标**: 差异化竞争优势

- [ ] **RAG 评估套件** ⭐⭐⭐⭐⭐
- [ ] **深度可解释性** ⭐⭐⭐⭐⭐
- [ ] **AI 辅助优化** ⭐⭐⭐⭐⭐
- [ ] **Agent 支持** ⭐⭐⭐⭐

**详见**: [COMPETITIVE_ANALYSIS.md](./COMPETITIVE_ANALYSIS.md)

---

## 🎯 使用场景导航

### 场景 1: 我是新手，想快速了解

**推荐路径**:
1. 阅读 [QUICK_ACCESS.md](./QUICK_ACCESS.md) (5分钟)
2. 查看 [README.md](./README.md) 快速开始章节 (10分钟)
3. 启动服务并尝试创建流程

### 场景 2: 我要开发新功能

**推荐路径**:
1. 阅读 [frontend-v2/README.md](./frontend-v2/README.md) 了解架构
2. 查看 [PHASE3_PLAYGROUND_PLAN.md](./frontend-v2/PHASE3_PLAYGROUND_PLAN.md) 了解下一步
3. 参考 [COMPETITIVE_ANALYSIS.md](./COMPETITIVE_ANALYSIS.md) 理解战略方向

### 场景 3: 我遇到了 Bug

**推荐路径**:
1. 查看 [README.md](./README.md) 故障排除章节
2. 参考最近的修复报告：
   - [FIX_UNDO_REDO_BUG_REPORT.md](./frontend-v2/FIX_UNDO_REDO_BUG_REPORT.md)
   - [FIX_UNDO_SAVE_REPORT.md](./frontend-v2/FIX_UNDO_SAVE_REPORT.md)
3. 使用测试清单验证：[UNDO_REDO_TEST_CHECKLIST.md](./frontend-v2/UNDO_REDO_TEST_CHECKLIST.md)

### 场景 4: 我想了解战略规划

**推荐路径**:
1. 阅读 [COMPETITIVE_ANALYSIS.md](./COMPETITIVE_ANALYSIS.md) (30分钟)
2. 查看 [COMPETITIVE_STRATEGY_QUICKREF.md](./COMPETITIVE_STRATEGY_QUICKREF.md) (5分钟)
3. 了解详细路线图：[docs/STUDIO_EVOLUTION_ROADMAP.md](./docs/STUDIO_EVOLUTION_ROADMAP.md)

---

## 🔧 开发者资源

### API 文档
- 后端 API: http://localhost:8080/docs (FastAPI Swagger UI)
- 前端组件: 见 [frontend-v2/src/components/](./frontend-v2/src/components/)

### 测试
```bash
# 验证 Phase 1 功能
python verify_standalone.py

# 前端类型检查
cd frontend-v2
npm run type-check
npm run lint
```

### 调试
```bash
# 查看端口占用
lsof -i :3000  # 前端
lsof -i :8080  # 后端

# 查看进程
ps aux | grep vite
ps aux | grep uvicorn
```

---

## ⚡ 常用命令

### 启动服务
```bash
# 后端
cd /home/chaotic/SAGE/packages/sage-studio
python -m sage.studio.config.backend.api &

# 前端
cd frontend-v2
npm run dev
```

### 代码质量
```bash
cd frontend-v2
npm run lint          # 检查
npm run lint:fix      # 自动修复
npm run type-check    # TypeScript 检查
```

### 构建部署
```bash
cd frontend-v2
npm run build        # 生产构建
npm run preview      # 预览构建结果
```

---

## 📞 获取帮助

### 问题排查优先级

1. **启动问题** → [README.md](./README.md) 故障排除
2. **功能问题** → [QUICK_ACCESS.md](./QUICK_ACCESS.md) 常见问题
3. **Bug 验证** → 相关测试清单
4. **新功能开发** → Phase 3 规划文档

### 文档更新

文档持续更新中，如发现过时内容，请参考：
- 最新代码：`frontend-v2/src/`
- 最新进度：`QUICK_ACCESS.md`
- 更新日志：`frontend-v2/CHANGELOG.md`

---

## 🎉 关键成就

- ✅ **Phase 1 完成**: 独立运行能力，11/11 测试通过
- ✅ **Phase 2 完成**: React 可视化编辑器，100% 功能完整
- ✅ **Bug 修复**: 撤销/重做优化，状态轮询实现

---

**最后更新**: 2025-10-17  
**维护者**: SAGE Studio Team  
**分支**: refactor/studio
