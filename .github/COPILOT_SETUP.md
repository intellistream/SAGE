# VS Code Copilot 配置指南

## 自动配置（推荐）

**VS Code 会自动读取 `.github/copilot-instructions.md` 文件**，无需手动配置。

### 验证 Copilot 是否读取指令

1. 打开 VS Code 的 Copilot Chat
2. 输入：`@workspace what are the SAGE architecture layers?`
3. 如果 Copilot 回答包含 L1-L5 层次结构，说明指令已生效

### 如果指令未生效

尝试以下步骤：

#### 1. 重新加载 VS Code
```
Ctrl+Shift+P → "Developer: Reload Window"
```

#### 2. 检查 Copilot 扩展
- 确保 "GitHub Copilot" 扩展已启用
- 确保 "GitHub Copilot Chat" 扩展已启用
- 版本建议：最新版本

#### 3. 检查 Copilot 设置
打开 VS Code 设置 (Ctrl+,)，搜索 "copilot"：

- ✅ `github.copilot.enable` = `true`
- ✅ `github.copilot.advanced` → 无需特殊配置

#### 4. 检查工作区
确保你在 SAGE 项目的根目录打开 VS Code：
```bash
cd /home/shuhao/SAGE
code .
```

#### 5. 手动指定指令文件（如果自动检测失败）
在 VS Code 设置中添加：
```json
{
  "github.copilot.advanced": {
    "instructionsFile": "${workspaceFolder}/.github/copilot-instructions.md"
  }
}
```

## Chat Mode 配置（可选）

**Chat Mode 是可选的个性化配置**，用于 Copilot Chat 特定模式。

### 创建 Chat Mode

1. 复制模板：
```bash
cp .github/sage.chatmode.md.example .github/chatmodes/sage.chatmode.md
```

2. (可选) 根据个人偏好编辑：
```bash
vim .github/chatmodes/sage.chatmode.md
```

3. 在 VS Code Copilot Chat 中选择 "sage" 模式

**注意：Chat mode 是用户本地配置，不会提交到 Git**

## 文件架构

```
.github/
├── copilot-instructions.md         # ✅ 主指令（VS Code 自动读取）
├── sage.chatmode.md.example        # ✅ Chat mode 模板
├── chatmodes/
│   └── sage.chatmode.md            # ❌ 用户本地配置（gitignored）
└── COPILOT_SETUP.md                # 📖 本文档
```

## 常见问题

### Q: 为什么我看不到 Copilot 使用 SAGE 规则？

**A:** 检查以下几点：

1. ✅ 确认文件存在：`ls -la .github/copilot-instructions.md`
2. ✅ 在项目根目录打开 VS Code
3. ✅ 重新加载窗口
4. ✅ 测试 Copilot 响应（询问 SAGE 架构问题）

### Q: Chat mode 和 copilot-instructions 有什么区别？

**A:**

- **copilot-instructions.md**: 所有 Copilot 功能（inline, chat, PR review）都会读取
- **sage.chatmode.md**: 仅用于 Copilot Chat 的特定模式，可以个性化定制

### Q: 我需要配置 Chat mode 吗？

**A:** **不需要**。主 instructions 文件已经足够。Chat mode 是可选的个性化配置。

### Q: 如何更新 Copilot 指令？

**A:** 直接编辑 `.github/copilot-instructions.md`，然后重新加载 VS Code 窗口。

## 验证配置

运行此命令验证文件存在：

```bash
# 检查主指令文件
ls -lh .github/copilot-instructions.md

# 查看文件大小（应该约 48KB）
du -h .github/copilot-instructions.md

# 查看前 20 行
head -20 .github/copilot-instructions.md
```

期望输出：
```
-rw-r--r-- 1 user user 48K .github/copilot-instructions.md
48K     .github/copilot-instructions.md

# SAGE Copilot Instructions

## Overview
...
```

## 技术支持

如果问题仍未解决：

1. 查看 VS Code 输出：`Output` → `GitHub Copilot`
2. 检查 VS Code 开发者工具：`Help` → `Toggle Developer Tools`
3. 参考文档：`docs-public/docs_src/dev-notes/cross-layer/copilot-instructions-architecture.md`

## 相关文档

- **主指令文件**: `.github/copilot-instructions.md` (1149 lines)
- **架构文档**: `docs-public/docs_src/dev-notes/cross-layer/copilot-instructions-architecture.md`
- **Chat mode 模板**: `.github/sage.chatmode.md.example`
