# SAGE Studio 前端启动和测试指南

## 📋 项目概述

SAGE Studio 是一个基于 Angular 16 的低代码可视化数据流管道编辑器，主要功能包括：

- **Overview（概览）**: 显示所有作业状态和统计信息
- **Operator Editor（操作符编辑器）**: 创建和编辑数据处理操作符
- **Pipeline（管道编辑器）**: 可视化拖拽创建数据流管道  
- **Submit New Pipeline（提交新管道）**: 提交管道到后端执行

## 🚀 快速启动

### 前置条件
- Node.js 18+ 
- npm 或 yarn
- SAGE 后端服务（可选，支持 Mock 数据）

### 1. 安装依赖
```bash
# 使用 SAGE 命令安装依赖（推荐）
# 这会安装 npm 依赖到 .sage/studio/ 目录并创建符号链接
sage studio install

# 或者直接使用 npm（不推荐，会安装到项目目录）
cd ~/SAGE/packages/sage-tools/src/sage/tools/studio
npm install
```

**注意**: `sage studio install` 会将 node_modules 安装到 `~/.sage/studio/node_modules/` 并在项目目录创建符号链接，这样可以避免污染项目目录。

### 2. 启动开发服务器
```bash
# 使用 SAGE 命令启动（推荐）
sage studio start

# 或者直接使用 npm
npm start
# 或者
ng serve --port 4200 --host 0.0.0.0 --disable-host-check
```

### 3. 访问应用
- 前端地址: http://localhost:4200
- API文档: http://localhost:8080/docs (需要后端服务)

## 🔧 配置说明

### 环境配置文件
- `src/environments/environment.ts` - 开发环境配置
- `src/environments/environment.prod.ts` - 生产环境配置

### Mock 数据
当前配置已启用 Mock 数据模式 (`enableMockData: true`)，可以在没有后端的情况下测试前端功能。

## 🧪 功能测试

### 1. Overview 页面测试
- 访问: http://localhost:4200/overview
- 功能: 查看作业列表、状态筛选、分页
- 测试数据: 显示 2 个示例作业（RAG问答管道、数据处理管道）

### 2. Operator Editor 测试  
- 访问: http://localhost:4200/operator-editor
- 功能: 创建、编辑、删除操作符
- 测试数据: 3 个预设操作符（FileSource、SimpleRetriever、TerminalSink）

### 3. Pipeline Editor 测试
- 访问: http://localhost:4200/submit-new-pipeline  
- 功能: 拖拽创建数据流管道、连接操作符
- 测试: 从左侧操作符面板拖拽到画布创建节点

### 4. Job Information 测试
- 访问: http://localhost:4200/job/job_001
- 功能: 查看作业详情、性能监控、操作符拓扑图

## 🐛 故障排除

### 编译错误
如果遇到编译错误，检查：
1. Node.js 版本是否为 18+
2. 依赖是否完全安装 (`sage studio install`)
3. TypeScript 错误是否已修复

### API 调用失败
当前使用 Mock 数据，如需连接真实后端：
1. 确保后端服务运行在 http://localhost:8080
2. 在 `environment.ts` 中设置 `enableMockData: false`

### 端口冲突
如果 4200 端口被占用：
```bash
ng serve --port 4201
```

## 📁 项目结构

```
src/
├── app/
│   ├── pages/           # 页面组件
│   │   ├── overview/    # 概览页面
│   │   ├── operator-editor/ # 操作符编辑器
│   │   ├── pipeline/    # 管道编辑器
│   │   └── ...
│   ├── model/           # 数据模型
│   ├── services/        # 服务类
│   └── common/          # 通用组件
├── environments/        # 环境配置
└── assets/             # 静态资源
```

## 🔗 相关链接

- [Angular CLI 文档](https://angular.io/cli)
- [ng-zorro-antd 组件库](https://ng.ant.design/)
- [SAGE 项目文档](../../../../../../../docs/)

## 💡 开发建议

1. **使用 Mock 数据**: 便于前端开发和测试
2. **模块化开发**: 每个页面独立开发和测试
3. **类型安全**: 充分利用 TypeScript 的类型检查
4. **组件复用**: 将通用功能抽取为可复用组件

## 📝 已知问题

1. 某些 API 路径需要与后端团队确认
2. 管道编辑器的拖拽功能需要进一步优化
3. 部分组件的错误处理需要完善

## 🎯 后续任务

- [ ] 完善 API 接口对接
- [ ] 优化管道编辑器交互体验
- [ ] 增加单元测试覆盖
- [ ] 优化性能和加载速度
