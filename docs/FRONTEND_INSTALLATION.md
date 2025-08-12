# SAGE Frontend Installation Guide

SAGE 提供了多种前端界面选项，您可以根据需要选择安装。

## 快速安装

### 🎯 只需要 Python API 和命令行工具
```bash
pip install isage
```

### 🌐 需要 Web 界面 (FastAPI)
```bash
pip install isage[frontend]
# 或
pip install isage[web]
```

### 🎨 需要低代码界面 (Angular Studio)
```bash
pip install isage[studio]
# 然后运行前端环境安装脚本
./scripts/setup_frontend.sh
```

### 🚀 完整 UI 套件 (所有前端功能)
```bash
pip install isage[ui]
./scripts/setup_frontend.sh
```

## 前端组件说明

### 1. Web UI (FastAPI Web UI)
- **路径**: `packages/sage-common/src/sage/common/frontend/web_ui/`
- **技术栈**: Python + FastAPI + HTML
- **功能**: API 文档、健康检查、Web 管理界面
- **端口**: 8080
- **依赖**: 只需要 Python 依赖

**启动方式**:
```bash
cd packages/sage-common/src/sage/common/frontend/web_ui
python main.py start
# 或使用 sage 命令
sage web-ui start
# 访问: http://localhost:8080
```

### 2. Studio (Angular 低代码界面)
- **路径**: `packages/sage-common/src/sage/common/frontend/studio/`
- **技术栈**: Angular 16 + TypeScript + ng-zorro-antd
- **功能**: 可视化管道编辑、代码生成、数据流设计
- **端口**: 4200
- **依赖**: 需要 Node.js 18+ 和 npm

**启动方式**:
```bash
cd packages/sage-common/src/sage/common/frontend/studio
npm start
# 访问: http://localhost:4200
```

## 自动化安装

使用提供的安装脚本可以自动配置前端环境：

```bash
./scripts/setup_frontend.sh
```

该脚本会：
1. 🔍 检测操作系统和现有环境
2. 📦 自动安装 Node.js 18+ (如果需要)
3. 🔧 安装 Angular Studio 的 npm 依赖
4. 📝 创建便捷的启动脚本
5. 📋 显示详细的使用说明

## 手动安装

如果自动安装失败，可以手动安装：

### 安装 Node.js (Studio 需要)

**Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**macOS:**
```bash
brew install node@18
```

**其他系统:**
访问 [Node.js 官网](https://nodejs.org/) 下载安装

### 安装 Angular 依赖
```bash
cd packages/sage-common/src/sage/common/frontend/studio
npm install
```

## 启动脚本

安装完成后，项目根目录会生成便捷的启动脚本：

```bash
# 启动 Web UI
./start_web_ui.sh

# 启动 Studio
./start_studio.sh
```

## 开发模式

对于开发者，可以使用开发模式启动：

**Web UI (开发模式):**
```bash
cd packages/sage-common/src/sage/common/frontend/web_ui
python main.py start --reload --host 0.0.0.0
# 或使用 sage 命令
sage web-ui start --reload --host 0.0.0.0
```

**Studio (开发模式):**
```bash
cd packages/sage-common/src/sage/common/frontend/studio
ng serve --host 0.0.0.0 --port 4200
```

## 故障排除

### Node.js 版本问题
```bash
node --version  # 应该 >= 18.0.0
npm --version   # 应该 >= 8.0.0
```

### npm 安装失败
```bash
# 清理缓存
npm cache clean --force
# 删除 node_modules 重新安装
rm -rf node_modules package-lock.json
npm install
```

### 端口冲突
- SAGE Server 默认端口: 8080
- Studio 默认端口: 4200

可以通过参数修改：
```bash
python main.py start --port 8081
ng serve --port 4201
```

## 生产部署

对于生产环境，建议：

1. **构建 Studio 静态文件**:
```bash
cd packages/sage-common/src/sage/common/frontend/studio
npm run build
```

2. **使用反向代理** (如 nginx) 统一前端服务

3. **配置 HTTPS** 和适当的安全策略
