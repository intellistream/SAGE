# Unified Gateway 开发任务

> **目标**: 合并 Issue #1287 (Gateway 合并) 和 Issue #1295 (动态引擎发现)，实现统一的 SAGE Gateway 服务。
>
> **分支**: `feature/unified-gateway`
>
> **相关 Issue**: #1287, #1295

---

## 📋 任务概览

本项目分为 **3 个串行任务组**，每组内的任务可并行执行：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 任务组 1: Control Plane 动态引擎管理                                         │
│ ├── Task 1A: 引擎注册与生命周期管理                                          │
│ └── Task 1B: 动态后端发现                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 任务组 2: Gateway 统一                                                       │
│ ├── Task 2A: sage-gateway 集成 Control Plane + 移除 UnifiedAPIServer        │
│ └── Task 2B: CLI 命令统一 (sage gateway + 更新 sage llm/studio)              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 任务组 3: 测试与文档                                                          │
│ ├── Task 3A: 集成测试                                                        │
│ └── Task 3B: 文档更新                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 任务组 1: Control Plane 动态引擎管理

> **前置条件**: 无
> **预计耗时**: 4-6 小时

### Task 1A: 引擎注册与生命周期管理

**提示词**:
```
你正在为 SAGE Control Plane 实现完整的引擎注册和生命周期管理。

当前问题:
- 引擎启动后不会自动注册到 Control Plane
- 没有统一的引擎状态跟踪
- 没有优雅关闭机制

需要实现:
1. EngineState 枚举: STARTING → READY → DRAINING → STOPPED → ERROR
2. EngineInfo 数据类: id, model, port, state, created_at, last_heartbeat
3. 引擎注册/注销 API: register_engine(), unregister_engine()
4. 心跳机制: 定期健康检查，连续 3 次失败进入 ERROR 状态
5. 优雅关闭: DRAINING 状态等待请求完成后再 STOPPED
6. HTTP 端点: POST /v1/management/engines/register

关键文件:
- sageLLM/control_plane/types.py: 新建，EngineState 和 EngineInfo
- sageLLM/control_plane/manager.py: 添加注册和状态管理逻辑
- sageLLM/control_plane/engine_lifecycle.py: 引擎启动后自动注册
- unified_api_server.py: 添加注册端点（临时，后续移除此文件）
```

**目标**: 实现引擎自动注册、状态跟踪和优雅关闭

**改动范围**:
| 文件 | 改动 |
|------|------|
| `sageLLM/control_plane/types.py` | 新建，定义 `EngineState` 和 `EngineInfo` |
| `sageLLM/control_plane/manager.py` | 添加 `register_engine()`, `unregister_engine()`, `get_engine_state()` |
| `sageLLM/control_plane/engine_lifecycle.py` | 引擎启动后调用注册，添加心跳和优雅关闭 |
| `unified_api_server.py` | 添加 `POST /v1/management/engines/register` |
| `sage/cli/commands/apps/llm.py` | 添加 `--drain` 选项到 `engine stop` |

**验收标准**:
- [ ] `sage llm engine start <model>` 后，引擎自动出现在 Control Plane
- [ ] `sage llm engine stop --drain <id>` 等待请求完成后停止
- [ ] 连续 3 次健康检查失败后引擎进入 ERROR 状态

---

### Task 1B: 动态后端发现

**提示词**:
```
你正在增强 UnifiedInferenceClient 以支持动态后端发现。

当前问题:
- UnifiedInferenceClient.create() 只检测第一个可用端点
- 新启动的引擎无法被发现
- 后端下线时 Client 不知道

需要实现:
1. GET /v1/management/backends 端点: 返回所有已注册后端
2. UnifiedInferenceClient 后台刷新: 每 30 秒刷新后端列表
3. 后端变更时的请求路由: 自动切换到可用后端
4. 故障转移: 后端不可用时自动路由到其他后端

关键文件:
- unified_client.py: 添加 _refresh_backends() 和后台线程
- sageLLM/control_plane/manager.py: 添加 get_registered_backends()
- unified_api_server.py: 添加 GET /v1/management/backends

注意: unified_api_server.py 的改动是临时的，任务组 2 会将这些端点迁移到 sage-gateway。
```

**目标**: 实现后端动态发现和自动故障转移

**改动范围**:
| 文件 | 改动 |
|------|------|
| `unified_client.py` | 添加 `_refresh_backends()` 和后台刷新线程 |
| `sageLLM/control_plane/manager.py` | 添加 `get_registered_backends()` |
| `unified_api_server.py` | 添加 `GET /v1/management/backends` |

**验收标准**:
- [ ] 新启动的引擎在 30 秒内被 Client 发现
- [ ] 后端下线时 Client 自动路由到其他可用后端
- [ ] Client 无可用后端时抛出明确异常

---

## 任务组 2: Gateway 统一

> **前置条件**: 任务组 1 完成
> **预计耗时**: 4-5 小时

### Task 2A: sage-gateway 集成 Control Plane + 移除 UnifiedAPIServer

**提示词**:
```
你正在将 Control Plane 功能迁移到 sage-gateway，并移除 UnifiedAPIServer。

当前状态:
- sage-gateway: 会话管理、RAG、Chat 代理，无 Control Plane
- UnifiedAPIServer: LLM/Embedding 代理 + Control Plane，需要移除

需要实现:
1. 在 sage-gateway 中创建 control_plane.py 路由模块
2. 迁移所有 Control Plane 端点到 sage-gateway:
   - GET /v1/management/engines
   - POST /v1/management/engines/start
   - POST /v1/management/engines/stop
   - POST /v1/management/engines/register
   - GET /v1/management/backends
   - GET /v1/management/gpu
3. 添加 LLM/Embedding 代理路由 (如果 sage-gateway 没有)
4. 删除 unified_api_server.py 文件
5. 更新 sage-common 的 __init__.py 导出

关键文件:
- packages/sage-gateway/src/sage/gateway/routes/control_plane.py: 新建
- packages/sage-gateway/src/sage/gateway/app.py: 挂载 Control Plane 路由
- packages/sage-common/src/sage/common/components/sage_llm/unified_api_server.py: 删除
- packages/sage-common/src/sage/common/components/sage_llm/__init__.py: 移除导出
```

**目标**: 将 Control Plane 迁移到 sage-gateway，删除 UnifiedAPIServer

**改动范围**:
| 文件 | 改动 |
|------|------|
| `sage-gateway/src/sage/gateway/routes/control_plane.py` | 新建，所有 Control Plane 端点 |
| `sage-gateway/src/sage/gateway/app.py` | 挂载 Control Plane 路由 |
| `sage-gateway/pyproject.toml` | 添加对 sage-common 的依赖 |
| `sage-common/.../unified_api_server.py` | **删除** |
| `sage-common/.../sage_llm/__init__.py` | 移除 UnifiedAPIServer 导出 |

**验收标准**:
- [ ] sage-gateway 包含所有 Control Plane 端点
- [ ] unified_api_server.py 已删除
- [ ] 现有 sage-gateway 功能不受影响

---

### Task 2B: CLI 命令统一

**提示词**:
```
你正在统一 SAGE CLI 命令，创建 sage gateway 命令组。

需要实现:
1. 新建 sage gateway 命令组:
   - `sage gateway start`: 启动 Gateway (端口 8000)
   - `sage gateway stop`: 停止 Gateway
   - `sage gateway status`: 显示状态和已注册引擎
   - `sage gateway logs`: 查看日志

2. 更新 sage llm engine 命令:
   - 使用 sage-gateway 的端点 (不再使用 UnifiedAPIServer)
   - Gateway 未运行时提示: "请先运行 sage gateway start"

3. 更新 sage studio start:
   - 现在启动的 Gateway 已包含 Control Plane
   - 更新启动提示信息

关键文件:
- sage-cli/src/sage/cli/commands/apps/gateway.py: 新建
- sage-cli/src/sage/cli/commands/apps/llm.py: 更新 engine 命令
- sage-cli/src/sage/cli/commands/apps/studio.py: 更新提示信息
- sage-cli/src/sage/cli/main.py: 注册 gateway 命令
```

**目标**: 创建 sage gateway 命令，统一 CLI 入口

**改动范围**:
| 文件 | 改动 |
|------|------|
| `sage-cli/src/sage/cli/commands/apps/gateway.py` | 新建 |
| `sage-cli/src/sage/cli/commands/apps/llm.py` | 更新 engine 命令 |
| `sage-cli/src/sage/cli/commands/apps/studio.py` | 更新提示信息 |
| `sage-cli/src/sage/cli/main.py` | 注册 gateway 命令 |

**验收标准**:
- [ ] `sage gateway start/stop/status/logs` 正常工作
- [ ] `sage llm engine list` 使用 sage-gateway 端点
- [ ] `sage studio start` 启动的 Gateway 包含 Control Plane

---

## 任务组 3: 测试与文档

> **前置条件**: 任务组 2 完成
> **预计耗时**: 3-4 小时

### Task 3A: 集成测试

**提示词**:
```
你正在为统一 Gateway 编写集成测试。

测试场景:
1. Gateway 启动/停止
2. 引擎注册: 启动引擎后自动出现在列表
3. 引擎生命周期: STARTING → READY → DRAINING → STOPPED
4. 动态后端发现: Client 能发现新启动的引擎
5. 故障转移: 后端下线时请求路由到其他后端

测试文件:
- packages/sage-gateway/tests/integration/test_control_plane.py
- packages/sage-common/tests/integration/test_dynamic_discovery.py

使用 pytest + httpx 进行异步测试，Mock vLLM 服务。
```

**目标**: 编写关键场景的集成测试

**改动范围**:
| 文件 | 改动 |
|------|------|
| `sage-gateway/tests/integration/test_control_plane.py` | 新建 |
| `sage-common/tests/integration/test_dynamic_discovery.py` | 新建 |

**验收标准**:
- [ ] 测试覆盖所有关键场景
- [ ] CI 通过

---

### Task 3B: 文档更新

**提示词**:
```
你正在更新文档以反映统一 Gateway 的变更。

需要更新:
1. docs/dev-notes/l1-common/README.md:
   - Quickstart 使用 `sage gateway start`
   - 移除两个 Gateway 的说明（现在只有一个）
   - 更新 CLI 命令参考

2. .github/copilot-instructions.md:
   - 更新 sageLLM 架构部分
   - 移除 UnifiedAPIServer 相关内容
   - 添加 `sage gateway` 命令

3. CHANGELOG.md:
   - 记录 UnifiedAPIServer 移除
   - 记录 sage gateway 命令新增
```

**目标**: 更新所有相关文档

**改动范围**:
| 文件 | 改动 |
|------|------|
| `docs/dev-notes/l1-common/README.md` | 更新 Quickstart 和 CLI |
| `.github/copilot-instructions.md` | 更新架构说明 |
| `CHANGELOG.md` | 记录变更 |

**验收标准**:
- [ ] 文档中无 UnifiedAPIServer 引用
- [ ] Quickstart 使用 `sage gateway start`

---

## 📊 执行流程

```
┌─────────────────────────┐
│      任务组 1           │
│  Control Plane 核心     │
│  ┌─────┐   ┌─────┐     │
│  │ 1A  │ ∥ │ 1B  │     │  ← 可并行
│  └─────┘   └─────┘     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│      任务组 2           │
│    Gateway 统一         │
│  ┌─────┐   ┌─────┐     │
│  │ 2A  │ ∥ │ 2B  │     │  ← 可并行
│  └─────┘   └─────┘     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│      任务组 3           │
│    测试与文档           │
│  ┌─────┐   ┌─────┐     │
│  │ 3A  │ ∥ │ 3B  │     │  ← 可并行
│  └─────┘   └─────┘     │
└─────────────────────────┘
```

**预计总耗时**: 11-15 小时

---

## 🚀 开始执行

每个任务完成后:
1. 提交到 `feature/unified-gateway` 分支
2. 运行 `sage-dev quality`
3. 运行相关测试
4. 更新本文档标记完成状态

---

**创建日期**: 2025-12-03
**最后更新**: 2025-12-03
