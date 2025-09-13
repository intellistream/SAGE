# SAGE Studio 管理系统

## 🎯 概述

SAGE Studio 是一个低代码可视化数据流管道编辑器，现在已经完全集成到 SAGE CLI 命令系统中，提供简洁的启动和管理方式。

## 🏗️ 架构设计

### 1. 前端架构
- **框架**: Angular 16 + TypeScript
- **UI组件**: ng-zorro-antd
- **可视化**: D3.js, Cytoscape.js
- **代码编辑**: Monaco Editor, CodeMirror
- **端口**: 4200

### 2. 管理架构
```
SAGE CLI (sage studio)
    ↓
Studio CLI Command (Python)
    ↓
Studio Manager Script (Bash)
    ↓
Angular Dev Server (npm)
```

## 📁 文件结构

```
SAGE/
├── packages/sage-common/src/sage/common/
│   ├── cli/commands/studio.py          # CLI命令实现
│   └── frontend/studio/                # Angular项目
│       ├── src/app/                    # 应用源码
│       ├── package.json                # npm配置
│       └── STUDIO_GUIDE.md            # 详细指南
├── scripts/
│   ├── studio_manager.sh               # 管理脚本
│   └── studio_demo.sh                  # 演示脚本
└── README.md                           # 本文档
```

## 🚀 快速开始

### 前置条件
- Node.js 18+
- npm
- SAGE 环境已配置

### 1. 检查信息
```bash
sage studio info
```

### 2. 安装依赖
```bash
sage studio install
```

### 3. 启动服务
```bash
sage studio start
```

### 4. 访问应用
- 打开浏览器访问: http://localhost:4200
- 或者使用命令: `sage studio open`

## 🛠️ 管理命令

### 基础操作
```bash
# 启动服务
sage studio start

# 检查状态  
sage studio status

# 停止服务
sage studio stop

# 重启服务
sage studio restart
```

### 监控和调试
```bash
# 查看日志
sage studio logs

# 实时跟踪日志
sage studio logs --follow

# 在浏览器中打开
sage studio open
```

### 开发相关
```bash
# 开发模式启动
sage studio start --dev

# 安装/更新依赖
sage studio install

# 显示详细信息
sage studio info
```

## 🎨 Studio 功能特性

### 1. Overview（概览）
- 作业列表和状态监控
- 性能统计和图表
- 搜索和筛选功能

### 2. Operator Editor（操作符编辑器）
- 可视化代码编辑
- 语法高亮和自动完成
- 操作符管理和版本控制

### 3. Pipeline Editor（管道编辑器）
- 拖拽式管道设计
- 节点连接和配置
- 实时验证和预览

### 4. Job Management（作业管理）
- 作业提交和执行
- 实时状态监控
- 性能分析和调优

## 🔧 配置说明

### 环境配置
Studio 支持开发和生产环境配置：

```typescript
// src/environments/environment.ts
export const environment = {
  production: false,
  api: {
    baseUrl: 'http://localhost:8080',
    paths: {
      operators: '/api/operators',
      pipelines: '/api/pipelines',
      jobs: '/api/jobs'
    }
  },
  dev: {
    enableMockData: true,    # 开发时使用Mock数据
    enableDebugLogs: true
  }
};
```

### Mock数据模式
当前配置支持Mock数据模式，无需后端服务即可体验所有功能：
- 示例操作符：FileSource, SimpleRetriever, TerminalSink
- 示例作业：RAG问答管道, 数据处理管道
- 完整的性能监控数据

## 🐛 故障排除

### 常见问题

#### 1. 启动失败
```bash
# 检查Node.js版本
node --version  # 需要 18+

# 检查依赖
sage studio install

# 检查端口占用
netstat -tuln | grep :4200
```

#### 2. 编译错误
```bash
# 清理依赖重新安装
cd packages/sage-common/src/sage/common/frontend/studio
rm -rf node_modules package-lock.json
npm install
```

#### 3. 服务无法访问
```bash
# 检查服务状态
sage studio status

# 查看详细日志
sage studio logs

# 重启服务
sage studio restart
```

### 日志文件位置
- 主日志: `/tmp/sage-studio.log`
- PID文件: `/tmp/sage-studio.pid`

## 🔗 与其他组件集成

### 1. Web UI 后端
Studio 前端可以与 SAGE Web UI 后端集成：
```bash
# 启动Web UI后端
sage web-ui start

# 启动Studio前端  
sage studio start
```

### 2. SAGE 核心服务
Studio 可以连接到 SAGE 的核心服务进行实际的数据处理：
- 作业提交和管理
- 实时状态监控
- 性能数据收集

## 📈 性能优化

### 1. 开发环境
- 使用 `--dev` 模式启用热重载
- Mock数据减少后端依赖
- 源码映射便于调试

### 2. 生产环境
- 构建优化版本：`ng build --prod`
- 启用 Gzip 压缩
- CDN 加速静态资源

## 🔒 安全考虑

### 1. 开发模式警告
开发服务器使用了 `--disable-host-check`，仅用于开发环境。

### 2. 生产部署
生产环境应该：
- 使用HTTPS
- 配置适当的CORS策略
- 启用安全Headers

## 📚 扩展阅读

- [Studio 详细指南](packages/sage-common/src/sage/common/frontend/studio/STUDIO_GUIDE.md)
- [SAGE CLI 文档](packages/sage-common/src/sage/common/cli/README.md)
- [前端安装指南](docs/FRONTEND_INSTALLATION.md)

## 🎉 总结

SAGE Studio 现在提供了完整的管理体验：

✅ **统一命令**: 通过 `sage studio` 命令管理所有功能  
✅ **自动化部署**: 一键安装依赖和启动服务  
✅ **智能检测**: 自动检查环境和依赖  
✅ **灵活配置**: 支持开发和生产模式  
✅ **Mock数据**: 无需后端即可体验功能  
✅ **路径无关**: 脚本自动计算项目路径  

现在你可以轻松地启动和管理 SAGE Studio 了！🚀
