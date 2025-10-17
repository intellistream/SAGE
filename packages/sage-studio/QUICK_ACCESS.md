# 🚀 SAGE Studio v2.0 - 快速访问

**当前状态**: Phase 2 核心功能完成 (100%) ✅ | Phase 3 开始 🚀 

---

## 🎯 立即访问

### 前端界面
```
http://localhost:3000  或  http://localhost:3001
```
**技术**: React 18 + React Flow + Ant Design
**状态**: Phase 2 完成 ✅

### 后端 API
```
http://localhost:8080
```
**技术**: FastAPI + Python

### API 文档
```
http://localhost:8080/docs
```

---

## 🛠️ 快速命令

### 启动开发环境

```bash
# 启动后端
cd /home/chaotic/SAGE/packages/sage-studio && python -m sage.studio.config.backend.api 2>&1 &

# 启动前端：
cd /home/chaotic/SAGE/packages/sage-studio/frontend-v2
npm run dev
```

### 常用命令

```bash

# Phase 2 指南
cat docs/PHASE2_GUIDE.md

# 前端开发
cd frontend-v2
npm run dev          # 启动
npm run build        # 构建
npm run preview      # 预览

# 后端开发  
cd /home/chaotic/SAGE/packages/sage-studio
python verify_standalone.py  # 验证
sage studio start            # 启动 (Angular)
```

---

## 📚 文档导航

### 必读文档
- **[README.md](./README.md)** ⭐ - 项目主页和完整指南
- **[frontend-v2/CHANGELOG.md](./frontend-v2/CHANGELOG.md)** - 更新日志

### 战略规划 🎯
- **[COMPETITIVE_ANALYSIS.md](./COMPETITIVE_ANALYSIS.md)** ⭐⭐⭐⭐⭐ - 竞品分析 (LangFlow/Coze)
- **[COMPETITIVE_STRATEGY_QUICKREF.md](./COMPETITIVE_STRATEGY_QUICKREF.md)** ⚡ - 战略快速参考

### Phase 2 完成报告 ✅
- **[PHASE2_FINAL_COMPLETION_REPORT.md](./frontend-v2/PHASE2_FINAL_COMPLETION_REPORT.md)** ⭐ - 完成报告
- **[FIX_UNDO_REDO_BUG_REPORT.md](./frontend-v2/FIX_UNDO_REDO_BUG_REPORT.md)** - Bug 修复详情
- **[UNDO_REDO_TEST_CHECKLIST.md](./frontend-v2/UNDO_REDO_TEST_CHECKLIST.md)** - 测试清单

### Phase 3 规划 🔄
- **[PHASE3_PLAYGROUND_PLAN.md](./frontend-v2/PHASE3_PLAYGROUND_PLAN.md)** ⭐ - Playground 实施计划

---

## 📊 当前进度

```
Phase 1: 接口抽象        ████████████████████ 100% ✅
Phase 2: 可视化编辑器    ████████████████████ 100% ✅ (完成！)
Phase 3: 追平体验        ███░░░░░░░░░░░░░░░░░  15% � (进行中)
Phase 4: AI 智能辅助     ░░░░░░░░░░░░░░░░░░░░   0% 📋

总体进度: 54% | Phase 2 全部完成，开始 Phase 3
```

### Phase 2 已完成 ✅ (100%)
- [x] 流程保存/加载功能
- [x] 流程执行控制 (运行/停止)
- [x] 动态节点配置表单
- [x] 画布缩放控制
- [x] Angular/React Flow 格式兼容
- [x] **状态轮询** (自动更新节点状态) ✨ NEW!
- [x] **撤销/重做功能** ✨ NEW!
- [x] **键盘快捷键** (Ctrl+Z/Y/S, Delete) ✨ NEW!

### Phase 3 进行中 🔄 (15%)
- [x] 撤销/重做、键盘快捷键、状态轮询 ✅
- [ ] Playground (交互式调试面板) - 最高优先级 ⭐⭐⭐⭐⭐
- [ ] Tweaks (运行时参数覆盖)
- [ ] 模板库 (10+ 常见 RAG 模板)

---

## 💡 快速提示

### 查看服务状态
```bash
# 检查端口占用
lsof -i :3000  # 前端
lsof -i :8080  # 后端

# 检查进程
ps aux | grep vite
ps aux | grep uvicorn
```

### 重启服务
```bash
# 前端
cd frontend-v2
# Ctrl+C 停止
npm run dev

# 后端
sage studio stop
sage studio start
```

### 查看日志
```bash
# 前端日志（终端输出）
# 在运行 npm run dev 的终端查看

# 后端日志
sage studio logs --backend
```

---

## 🐛 常见问题

### 前端无法访问？
```bash
# 检查服务是否运行
lsof -i :3000

# 重启服务
cd frontend-v2
npm run dev
```

### API 请求失败？
```bash
# 确保后端运行
lsof -i :8080

# 启动后端
cd /home/chaotic/SAGE/packages/sage-studio
python -c "from src.sage.studio.config.backend.api import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8080)"
```

### 端口被占用？
```bash
# 杀死占用端口的进程
kill -9 $(lsof -t -i:3000)
kill -9 $(lsof -t -i:8080)
```

---

## 🎯 下一步开发

### Phase 3 核心功能 (追平体验)

#### 🔥 最高优先级 (P0)
1. **Playground** ⭐⭐⭐⭐⭐ - 交互式调试面板
   - 实时与流程对话
   - 显示中间步骤输出
   - WebSocket 实时通信
   - 预计: 3-5天

#### 高优先级 (P1)
2. **Tweaks** ⭐⭐⭐⭐ - 运行时参数覆盖
   - 快速实验不同配置
   - 无需修改流程
   - 预计: 2-3天

3. **模板库** ⭐⭐⭐⭐ - 降低入门门槛
   - 10+ 常见 RAG 模板
   - 一键导入使用
   - 预计: 3-5天

#### 中优先级 (P2)
4. **日志查看** - 集成 getJobLogs API
5. **流程验证** - 检查连接完整性和必填参数
6. **动态配置获取** - 从后端 API 获取节点配置定义

---

## 🎨 新增功能 (Phase 2 完成)

### ⌨️ 键盘快捷键
- `Ctrl/Cmd + Z` - 撤销
- `Ctrl/Cmd + Shift + Z` 或 `Ctrl/Cmd + Y` - 重做
- `Ctrl/Cmd + S` - 保存流程
- `Delete` / `Backspace` - 删除选中节点

### 🔄 状态轮询
- 流程运行时自动更新节点状态
- 节点边框颜色实时变化：
  - 🔵 运行中 (蓝色)
  - 🟢 已完成 (绿色)
  - 🔴 失败 (红色)
- 每秒自动轮询，完成后自动停止

### ↩️ 撤销/重做
- 支持最多 50 步历史记录
- 所有节点/边操作自动保存
- 工具栏按钮根据状态自动启用/禁用

---
