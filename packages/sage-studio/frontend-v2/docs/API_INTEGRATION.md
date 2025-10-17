# SAGE Studio v2.0 - API 集成文档

## 📡 API 服务层

已创建完整的 API 客户端服务 (`src/services/api.ts`)，封装了与 Phase 1 后端的所有通信。

### 基础配置

```typescript
// API 基础 URL
const API_BASE_URL = '/api'  // Vite 代理到 localhost:8080

// Axios 实例配置
- 超时时间: 10秒
- 自动错误处理
- JSON Content-Type
```

## 🔌 可用的 API 方法

### 1. 节点管理

#### `getNodes(): Promise<NodeDefinition[]>`
获取所有可用的节点定义

```typescript
import { getNodes } from '../services/api'

const nodes = await getNodes()
// 返回: [{ id, name, description, code, isCustom }, ...]
```

#### `getNodesList(page, size, search): Promise<{items, total}>`
分页获取节点列表，支持搜索

```typescript
const result = await getNodesList(1, 10, 'File')
// 返回: { items: [...], total: 100 }
```

### 2. 流程管理

#### `submitFlow(flowConfig): Promise<{status, pipeline_id, file_path}>`
提交流程配置到后端

```typescript
import { submitFlow } from '../services/api'

const result = await submitFlow({
  name: '示例流程',
  description: 'RAG问答系统',
  nodes: [...],
  edges: [...]
})
// 返回: { status: 'success', pipeline_id: 'pipeline_xxx', file_path: '...' }
```

### 3. 作业管理

#### `getAllJobs(): Promise<Job[]>`
获取所有作业信息

#### `getJobDetail(jobId): Promise<Job>`
获取作业详细信息（包含操作符拓扑结构）

#### `getJobStatus(jobId): Promise<JobStatus>`
获取作业运行状态

```typescript
const status = await getJobStatus('job_001')
// 返回: { job_id, status: 'running', use_ray, isRunning }
```

#### `startJob(jobId): Promise<{status, message}>`
启动作业

#### `stopJob(jobId, duration): Promise<{status, message}>`
停止作业

### 4. 日志管理

#### `getJobLogs(jobId, offset): Promise<JobLogs>`
增量获取作业日志

```typescript
let offset = 0
const logs = await getJobLogs('job_001', offset)
// 返回: { offset: 10, lines: ['log line 1', 'log line 2', ...] }
offset = logs.offset  // 下次请求使用新的 offset
```

### 5. 配置管理

#### `getPipelineConfig(pipelineId): Promise<{config}>`
获取管道配置（YAML格式）

#### `updatePipelineConfig(pipelineId, config): Promise<{status, message}>`
更新管道配置

### 6. 健康检查

#### `healthCheck(): Promise<{status, service}>`
检查后端服务健康状态

```typescript
const health = await healthCheck()
// 返回: { status: 'healthy', service: 'SAGE Studio Backend' }
```

## 🎯 已集成的组件

### NodePalette.tsx
- ✅ 从后端动态加载节点定义
- ✅ 显示加载状态和错误处理
- ✅ 支持搜索和分类
- ✅ 错误重试机制

**使用示例:**
```typescript
// NodePalette 组件启动时自动调用
const nodes = await getNodes()
setNodes(nodes)
```

### FlowEditor.tsx (待集成)
- ⏳ 将使用 `submitFlow()` 提交流程
- ⏳ 保存/加载功能

### Toolbar.tsx (待集成)
- ⏳ Run 按钮 → `startJob()`
- ⏳ Stop 按钮 → `stopJob()`
- ⏳ Save 按钮 → `submitFlow()`

## 🚀 启动后端服务

### 方法 1: 直接运行
```bash
cd /home/chaotic/SAGE/packages/sage-studio
python src/sage/studio/config/backend/api.py
```

### 方法 2: 后台运行
```bash
cd /home/chaotic/SAGE/packages/sage-studio
nohup python src/sage/studio/config/backend/api.py > /tmp/sage_studio_api.log 2>&1 &
```

### 检查服务状态
```bash
# 健康检查
curl http://localhost:8080/health

# 获取节点列表
curl http://localhost:8080/api/operators

# 查看日志
tail -f /tmp/sage_studio_api.log
```

## 🔧 Vite 代理配置

`vite.config.ts` 中已配置代理：

```typescript
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
```

这样前端可以通过 `/api/*` 访问后端，避免 CORS 问题。

## 📊 数据流向

```
Frontend (localhost:3000)
    ↓
Vite Dev Server (Proxy /api)
    ↓
Backend API (localhost:8080)
    ↓
.sage/ 目录
    ├── pipelines/      # 保存的流程配置
    ├── states/         # 作业状态
    └── operators/      # 节点定义
```

## 🐛 错误处理

API 客户端已配置统一的错误处理：

```typescript
// 自动捕获三种错误类型
1. 服务器返回错误 (4xx/5xx)
   → 抛出: Error(response.data.detail)

2. 网络错误 (无响应)
   → 抛出: Error('网络错误：无法连接到服务器')

3. 其他错误
   → 直接抛出原始错误
```

## 📝 TypeScript 类型定义

所有 API 方法都有完整的类型定义：

```typescript
export interface NodeDefinition {
  id: number
  name: string
  description: string
  code: string
  isCustom: boolean
}

export interface FlowConfig {
  name: string
  description?: string
  nodes: Array<{...}>
  edges: Array<{...}>
}

export interface Job {
  jobId: string
  name: string
  isRunning: boolean
  // ... 更多字段
}
```

## ✅ 测试结果

```bash
# 健康检查 ✅
$ curl http://localhost:8080/health
{"status":"healthy","service":"SAGE Studio Backend"}

# 节点列表 ✅  
$ curl http://localhost:8080/api/operators
[
  {
    "id": 8,
    "name": "TerminalSink",
    "description": "Writes the received message to the console",
    "code": "...",
    "isCustom": false
  },
  {
    "id": 9,
    "name": "FileSource",
    "description": "Read queries from a file",
    "code": "...",
    "isCustom": false
  },
  ...
]
```

## 🎯 下一步

1. ✅ ~~创建 API 服务层~~
2. ✅ ~~集成 NodePalette~~
3. ⏳ 实现 Toolbar 流程控制
4. ⏳ 实现流程保存/加载
5. ⏳ 实现实时日志查看
6. ⏳ 实现作业状态监控

---

**API 集成完成日期:** 2025-10-14  
**后端服务:** localhost:8080  
**前端服务:** localhost:3000
