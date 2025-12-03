# SAGE Studio 部署指南

## 概述

SAGE Studio 是一个基于 React + Vite 的前端应用，配合 Python 后端 API、Gateway 和本地 LLM 服务。本文档介绍部署相关的配置和注意事项。

## 前置依赖

### 系统依赖

1. **Node.js 18+** 和 **npm**（TypeScript 5.x 需要 Node.js 14+，推荐 18+）
   ```bash
   # 推荐通过 conda 安装（确保版本正确）
   conda install -y nodejs=20 -c conda-forge

   # 检查版本
   node --version  # 应该显示 v18+ 或 v20+

   # 如果系统有旧版本 Node.js，确保 conda 环境的优先级更高
   which node  # 应该指向 conda 环境中的 node
   ```

   **常见问题**：如果系统通过 apt 安装了旧版 Node.js（如 v12），可能会导致 TypeScript 编译失败（`SyntaxError: Unexpected token '?'`）。解决方法：
   - 使用 conda 安装 Node.js 20+
   - 或使用 nvm 管理 Node.js 版本：`nvm install 20 && nvm use 20`

2. **Python 3.10+** 和 SAGE 开发环境
   ```bash
   ./quickstart.sh --dev --yes
   ```

### 检查依赖

```bash
sage studio install  # 自动检测并提示缺失的依赖
```

## 部署模式

### 开发模式 (Dev Mode)

使用 Vite dev server，支持热更新，适合开发调试。

```bash
sage studio start --dev --host 0.0.0.0 --port 5173
```

特点：
- 无需预先构建
- 支持 HMR (Hot Module Replacement)
- 更快的启动速度

### 生产模式 (Production Mode)

使用 Vite preview server，基于预构建的静态资源，适合生产环境。

```bash
# 步骤 1: 安装前端依赖
sage studio install

# 步骤 2: 构建生产版本
sage studio build

# 步骤 3: 启动生产服务
sage studio start --prod --host 0.0.0.0 --port 5173
```

特点：
- 需要先执行 `build` 步骤
- 更高的性能和稳定性
- 优化后的静态资源

## 外部访问配置 (allowedHosts)

### 问题背景

Vite 5.x 有安全特性，默认拒绝来自非 `localhost` 的 Host 头请求。当通过反向代理（如 Cloudflare Tunnel、Nginx）访问时，会出现：

```
Blocked request. This host ("studio.sage.org.ai") is not allowed.
To allow this host, add "studio.sage.org.ai" to `server.allowedHosts` in vite.config.js.
```

### 解决方案

在 `vite.config.ts` 中配置 `allowedHosts: true`：

```typescript
// packages/sage-studio/src/sage/studio/frontend/vite.config.ts
export default defineConfig({
    server: {
        port: 5173,
        // 开发模式：允许所有外部 Host
        allowedHosts: true,
        proxy: { ... },
    },
    // 生产模式 (vite preview) 也需要配置
    preview: {
        port: 5173,
        allowedHosts: true,
    },
})
```

**注意**：`server` 配置仅对 `vite dev` 生效，`preview` 配置仅对 `vite preview` 生效。

## CI/CD 部署 (GitHub Actions)

### 部署流程

参考 `.github/workflows/deploy-studio.yml`：

```yaml
steps:
  # 1. 安装 Node.js
  - name: Install Frontend Dependencies
    run: |
      conda install -y nodejs=20 -c conda-forge
      sage studio install

  # 2. 构建生产版本
  - name: Build Studio (Production)
    run: sage studio build

  # 3. 启动服务
  - name: Start SAGE Studio
    run: |
      nohup sage studio start --prod --host 0.0.0.0 --port 5173 -y &
```

### 关键选项

- `--host 0.0.0.0`: 监听所有网络接口（必须，否则外部无法访问）
- `--port 5173`: 指定端口
- `-y`: 非交互模式，跳过所有确认提示
- `--prod`: 生产模式

### Cloudflare Tunnel 集成

```yaml
- name: Start Cloudflare Tunnel
  run: |
    nohup cloudflared tunnel run --token "$CLOUDFLARE_TUNNEL_TOKEN" &
```

Tunnel 会将外部域名（如 `studio.sage.org.ai`）代理到本地端口 5173。

## 常见问题

### 1. `tsc: not found`

**原因**：TypeScript 编译器未安装或 `node_modules` 不完整。

**解决**：
```bash
sage studio install  # 重新安装前端依赖
```

### 2. 端口未监听

**原因**：服务启动失败或使用了错误的 host。

**排查**：
```bash
# 检查端口监听
ss -tlnp | grep 5173

# 检查进程
ps aux | grep "sage studio"

# 查看日志
sage studio logs
```

### 3. 外部无法访问

**检查清单**：
1. 是否使用 `--host 0.0.0.0`
2. 防火墙是否开放端口
3. `allowedHosts` 是否配置正确
4. 反向代理是否正确转发

## 架构图

```
                    ┌─────────────────────────┐
                    │   Cloudflare Tunnel     │
                    │  (studio.sage.org.ai)   │
                    └───────────┬─────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────┐
│                    服务器 (0.0.0.0)                    │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │   Studio    │  │   Gateway   │  │   sageLLM    │  │
│  │  (Vite)     │  │   (8000)    │  │   (8901)     │  │
│  │   :5173     │  │             │  │              │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  │
│         │                │                │          │
│         └────────────────┴────────────────┘          │
│                     localhost                        │
└───────────────────────────────────────────────────────┘
```

## 相关文件

- `packages/sage-studio/src/sage/studio/frontend/vite.config.ts` - Vite 配置
- `packages/sage-studio/src/sage/studio/studio_manager.py` - Studio 管理器
- `.github/workflows/deploy-studio.yml` - CI/CD 部署流程
