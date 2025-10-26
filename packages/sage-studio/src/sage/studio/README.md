# SAGE Studio

SAGE Studio 是一个低代码可视化管道编辑器，提供图形化界面来构建和管理 SAGE 管道。

## 目录结构

```
studio/
├── frontend/           # Angular 前端应用
│   ├── src/           # 源代码
│   ├── angular.json   # Angular 配置
│   ├── package.json   # NPM 依赖
│   └── tsconfig.json  # TypeScript 配置
├── config/            # 配置文件
│   └── backend/       # 后端配置
├── data/              # 数据文件
│   └── operators/     # 操作符定义
├── docs/              # 文档
├── tools/             # 构建和部署脚本
│   ├── scripts/       # Shell 脚本
│   └── setup_config.py # 配置工具
├── dist/              # 构建输出（自动生成）
└── .angular/          # Angular 缓存（自动生成）
```

## 使用方法

### 安装依赖

```bash
sage studio install
```

### 构建应用

```bash
sage studio build
```

### 启动开发服务器

```bash
sage studio start --dev
```

### 启动生产服务器

```bash
sage studio start
```

### 其他命令

```bash
sage studio status    # 查看状态
sage studio stop      # 停止服务
sage studio logs      # 查看日志
sage studio open      # 在浏览器中打开
```

## 开发说明

- 前端源代码位于 `frontend/src/` 目录
- 构建输出位于 `dist/` 目录
- 依赖包安装到 `~/.sage/studio/node_modules` 并通过符号链接引用
- 配置文件存储在 `~/.sage/` 目录下

## 架构

- **前端**: Angular 16 + Ng-Zorro UI 组件库
- **图形库**: D3.js, Cytoscape.js
- **代码编辑**: Monaco Editor, CodeMirror
- **数据可视化**: ngx-charts
