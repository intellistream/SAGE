# SAGE Server 重命名为 Web UI 迁移文档

## 概述
为了提高命名清晰度和区分两个前端界面的用途，我们将 `sage_server` 重命名为 `web_ui`。

## 两个UI系统的定位

### 1. Web UI (原 sage_server)
- **路径**: `packages/sage-common/src/sage/common/frontend/web_ui/`
- **技术栈**: Python + FastAPI + HTML
- **目标用户**: 开发者和系统管理员
- **功能**: API 文档、健康检查、Web 管理界面
- **端口**: 8080
- **启动命令**: `web-ui start`

### 2. Studio
- **路径**: `packages/sage-common/src/sage/common/frontend/studio/`
- **技术栈**: Angular 16 + TypeScript + ng-zorro-antd
- **目标用户**: 业务用户
- **功能**: 低代码可视化管道编辑器
- **端口**: 4200
- **启动命令**: `ng serve`

## 主要改动

### 1. 目录结构变更
```
packages/sage-common/src/sage/common/frontend/
├── sage_server/  (删除)
├── web_ui/       (新建)
│   ├── __init__.py
│   ├── app.py
│   └── main.py
└── studio/       (保持不变)
```

### 2. 文件更新列表

#### 核心文件
- `packages/sage-common/src/sage/common/frontend/web_ui/app.py`
  - 更新 FastAPI 应用标题: "SAGE Web UI"
  - 更新描述: "Web 管理界面和 API 文档"
  - 更新服务名称和健康检查信息

- `packages/sage-common/src/sage/common/frontend/web_ui/main.py`
  - 更新命令行描述: "SAGE Web UI"
  - 更新示例命令路径
  - 更新启动信息显示

- `packages/sage-common/src/sage/common/frontend/web_ui/__init__.py`
  - 简化为直接导入本地 main 函数
  - 移除复杂的延迟导入逻辑

#### 配置文件
- `packages/sage-common/pyproject.toml`
  - 更新 entry point: `web-ui = "sage.common.frontend.web_ui.main:main"`

- `.vscode/settings.json`
  - 更新 Python 路径配置

- `.gitignore`
  - 更新日志目录路径

#### 文档文件
- `docs/FRONTEND_INSTALLATION.md`
  - 更新所有路径引用
  - 更新启动脚本名称
  - 更新功能描述

- `README.md`
  - 更新目录路径引用

- `packages/sage-common/README.md`
  - 更新目录结构说明

#### 脚本文件
- `scripts/setup_frontend.sh`
  - 更新启动脚本生成: `start_web_ui.sh`
  - 更新安装说明和路径
  - 更新帮助信息

- `packages/sage-middleware/.gitignore`
  - 更新日志目录路径

### 3. 新的命令行工具

#### 主要命令
```bash
# 新的统一命令结构
sage web-ui start               # 启动 Web UI
sage web-ui start --reload      # 开发模式
sage web-ui status              # 检查状态
sage web-ui info                # 显示信息

# 启动脚本 (运行 setup_frontend.sh 后生成)
./start_web_ui.sh              # 便捷启动 Web UI
./start_studio.sh              # 便捷启动 Studio
```

#### 命令架构改进
- Web UI 现在作为 `sage` 主命令的子命令，而不是独立的 `web-ui` 命令
- 保持了命令的一致性和可发现性
- 支持完整的帮助系统：`sage web-ui --help`

#### 开发模式
```bash
# Web UI 开发模式
cd packages/sage-common/src/sage/common/frontend/web_ui
python main.py start --reload --host 0.0.0.0
# 或使用统一命令
sage web-ui start --reload --host 0.0.0.0

# Studio 开发模式
cd packages/sage-common/src/sage/common/frontend/studio
ng serve --host 0.0.0.0
```

## 验证测试

### 1. 功能测试
- ✅ Web UI 可以正常启动
- ✅ FastAPI 应用正常运行在 8080 端口
- ✅ API 文档可访问: http://localhost:8080/docs
- ✅ 健康检查正常: http://localhost:8080/health
- ✅ 命令行工具 `web-ui` 正常工作

### 2. 安装测试
- ✅ `pip install -e .` 正常安装
- ✅ Entry points 正确注册
- ✅ 包导入无错误

## 升级指南

对于现有用户，需要进行以下更新：

### 1. 重新安装包
```bash
cd packages/sage-common
pip install -e .
```

### 2. 更新启动方式
```bash
# 旧方式 (已废弃)
sage-server start
web-ui start

# 新方式
sage web-ui start
```

### 3. 更新脚本和配置
如果有自定义脚本引用了旧路径，需要更新：
- `sage_server` → `web_ui`
- `sage-server` → `web-ui`

## 向后兼容性

为了平滑过渡，建议：
1. 保留旧的启动脚本一段时间并添加废弃警告
2. 在文档中明确说明新的命名约定
3. 逐步更新所有相关脚本和文档

## 总结

这次重命名明确了两个UI系统的定位：
- **Web UI**: 面向开发者的管理界面，提供API文档和系统监控
- **Studio**: 面向业务用户的低代码可视化编辑器

新的命名更加直观，有助于用户理解各组件的用途。

迁移完成后，所有功能正常，命令行工具可用，文档已更新。
