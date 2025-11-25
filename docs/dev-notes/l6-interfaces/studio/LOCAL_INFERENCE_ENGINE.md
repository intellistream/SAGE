# Studio 本地推理引擎集成方案

## 概述

在 SAGE Studio 中集成本地推理引擎管理功能，允许用户：
1. 一键启动/停止本地 vLLM 服务
2. 在 Chat 页面选择使用本地服务或云端 API
3. 查看本地服务状态和资源使用情况

## 架构设计

### 1. 后端 API 端点

**位置**: `packages/sage-studio/src/sage/studio/config/backend/api.py`

```python
# ==================== Local Inference Engine Management ====================

class LocalEngineStatus(BaseModel):
    """本地推理引擎状态"""
    running: bool
    port: int | None = None
    model: str | None = None
    pid: int | None = None
    gpu_memory_usage: float | None = None  # GB
    uptime: str | None = None

class LocalEngineStartRequest(BaseModel):
    """启动本地推理引擎请求"""
    model: str  # 例如: "Qwen/Qwen2.5-7B-Instruct"
    port: int = 8001  # 默认 8001 避免与 Gateway 冲突
    gpu_memory_utilization: float = 0.9
    quantization: str | None = None  # "awq", "gptq", None

@app.get("/api/local-engine/status")
async def get_local_engine_status() -> LocalEngineStatus:
    """获取本地推理引擎状态"""
    # 检测 vLLM 进程
    # 查询 GPU 使用情况
    pass

@app.post("/api/local-engine/start")
async def start_local_engine(request: LocalEngineStartRequest):
    """启动本地推理引擎"""
    # 使用 subprocess 启动 vLLM server
    # 后台运行，保存 PID
    pass

@app.post("/api/local-engine/stop")
async def stop_local_engine():
    """停止本地推理引擎"""
    # 根据 PID 停止进程
    pass

@app.get("/api/local-engine/models")
async def list_available_models():
    """列出可用的本地模型"""
    # 扫描 ~/.cache/huggingface/hub/
    # 返回已下载的模型列表
    pass
```

### 2. 前端 UI 组件

**位置**: `packages/sage-studio/src/sage/studio/frontend/src/components/LocalEnginePanel.tsx`

#### 2.1 主面板布局

```tsx
/**
 * 本地推理引擎管理面板
 * 位置：Studio 顶部导航或侧边栏
 */
export default function LocalEnginePanel() {
  const [status, setStatus] = useState<LocalEngineStatus>()
  const [isStarting, setIsStarting] = useState(false)

  return (
    <Card title="本地推理引擎">
      {/* 状态指示器 */}
      <StatusIndicator status={status} />

      {/* 控制按钮 */}
      {!status?.running ? (
        <StartEngineForm onStart={handleStart} />
      ) : (
        <RunningEngineInfo status={status} onStop={handleStop} />
      )}
    </Card>
  )
}
```

#### 2.2 启动表单

```tsx
function StartEngineForm({ onStart }) {
  return (
    <Form onFinish={onStart}>
      <Form.Item label="选择模型">
        <Select placeholder="选择本地模型">
          <Option value="Qwen/Qwen2.5-7B-Instruct">
            Qwen 2.5 7B (推荐)
          </Option>
          <Option value="Qwen/Qwen2.5-1.5B-Instruct">
            Qwen 2.5 1.5B (低显存)
          </Option>
          {/* 动态加载用户已下载的模型 */}
        </Select>
      </Form.Item>

      <Form.Item label="GPU 显存占用">
        <Slider min={0.5} max={0.95} step={0.05} defaultValue={0.9} />
      </Form.Item>

      <Form.Item label="端口">
        <InputNumber defaultValue={8001} disabled />
        <Text type="secondary">推荐使用 8001（避免与 Gateway 冲突）</Text>
      </Form.Item>

      <Button type="primary" htmlType="submit" loading={isStarting}>
        🚀 启动推理引擎
      </Button>
    </Form>
  )
}
```

#### 2.3 运行状态显示

```tsx
function RunningEngineInfo({ status, onStop }) {
  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Statistic title="模型" value={status.model} />
      <Statistic title="端口" value={status.port} />
      <Statistic
        title="GPU 显存"
        value={status.gpu_memory_usage}
        suffix="GB"
      />
      <Statistic title="运行时间" value={status.uptime} />

      <Button danger onClick={onStop}>
        🛑 停止推理引擎
      </Button>
    </Space>
  )
}
```

### 3. Chat 页面 LLM 源选择

**位置**: `packages/sage-studio/src/sage/studio/frontend/src/components/ChatPanel.tsx`

```tsx
function ChatPanel() {
  const [llmSource, setLlmSource] = useState<'local' | 'cloud'>('auto')
  const [localEngineStatus, setLocalEngineStatus] = useState()

  return (
    <div>
      {/* LLM 源选择器 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Text>LLM 来源：</Text>
          <Radio.Group
            value={llmSource}
            onChange={(e) => setLlmSource(e.target.value)}
          >
            <Radio value="auto">
              <Tooltip title="优先使用本地，不可用时降级到云端">
                🤖 自动（推荐）
              </Tooltip>
            </Radio>
            <Radio value="local" disabled={!localEngineStatus?.running}>
              <Tooltip title="仅使用本地推理引擎">
                💻 本地
              </Tooltip>
            </Radio>
            <Radio value="cloud">
              <Tooltip title="使用云端 API (需配置 API Key)">
                ☁️ 云端
              </Tooltip>
            </Radio>
          </Radio.Group>

          {/* 状态指示 */}
          {localEngineStatus?.running && (
            <Tag color="success">本地引擎运行中</Tag>
          )}
        </Space>
      </Card>

      {/* 聊天界面 */}
      <ChatInterface llmSource={llmSource} />
    </div>
  )
}
```

### 4. 实现优先级

#### Phase 1: 基础功能（1-2 天）
- [ ] 后端 API: 状态检测、启动、停止
- [ ] 前端: 基础状态显示和控制按钮
- [ ] Chat 页面: LLM 源选择器

#### Phase 2: 增强功能（2-3 天）
- [ ] 模型列表动态加载
- [ ] GPU 使用情况监控
- [ ] 启动进度显示（模型加载）
- [ ] 日志查看

#### Phase 3: 高级功能（3-5 天）
- [ ] 模型下载管理
- [ ] 多模型切换
- [ ] 性能监控图表
- [ ] 推理参数调优

## 技术细节

### 启动 vLLM Server

```python
# backend/api.py
import subprocess
from pathlib import Path

async def start_vllm_server(model: str, port: int = 8001, **kwargs):
    """启动 vLLM 服务器"""

    # 构建启动命令
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--host", "0.0.0.0",
        "--port", str(port),
        "--gpu-memory-utilization", str(kwargs.get("gpu_memory_utilization", 0.9)),
    ]

    if kwargs.get("quantization"):
        cmd.extend(["--quantization", kwargs["quantization"]])

    # 后台启动
    log_file = Path.home() / ".sage" / "studio" / f"vllm_{port}.log"
    log_handle = open(log_file, "w")

    process = subprocess.Popen(
        cmd,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    # 保存 PID
    pid_file = Path.home() / ".sage" / "studio" / f"vllm_{port}.pid"
    pid_file.write_text(str(process.pid))

    return {
        "pid": process.pid,
        "port": port,
        "log_file": str(log_file),
    }
```

### 状态检测

```python
import psutil
import requests

def get_vllm_status(port: int = 8001):
    """检测 vLLM 服务状态"""

    # 检查端口
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=1)
        if response.status_code == 200:
            # 获取模型信息
            models_response = requests.get(f"http://localhost:{port}/v1/models")
            models = models_response.json().get("data", [])

            return {
                "running": True,
                "port": port,
                "model": models[0]["id"] if models else None,
            }
    except:
        pass

    return {"running": False}
```

### GPU 监控

```python
try:
    import pynvml

    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    info = pynvml.nvmlDeviceGetMemoryInfo(handle)

    gpu_memory_usage = info.used / 1024**3  # GB
except:
    gpu_memory_usage = None
```

## 环境变量支持

```bash
# .env
# 本地推理引擎默认设置
SAGE_LOCAL_ENGINE_PORT=8001
SAGE_LOCAL_ENGINE_DEFAULT_MODEL=Qwen/Qwen2.5-7B-Instruct
SAGE_LOCAL_ENGINE_GPU_UTIL=0.9
```

## 用户体验流程

### 场景 1: 首次使用
1. 用户打开 Studio Chat 页面
2. 看到提示："本地推理引擎未启动，正在使用云端 API"
3. 点击"启动本地引擎"按钮
4. 选择模型（如果已下载）或下载新模型
5. 点击"启动"，等待加载（显示进度）
6. 启动成功，自动切换到本地服务
7. 开始对话，响应速度更快

### 场景 2: 已有本地服务
1. 用户在终端启动了 vLLM: `sage llm run Qwen/Qwen2.5-7B-Instruct --port 8001`
2. 打开 Studio Chat 页面
3. 自动检测到本地服务，显示："✅ 正在使用本地推理引擎"
4. 可选择切换到云端 API

## 安全考虑

1. **进程隔离**: vLLM 进程独立运行，崩溃不影响 Studio
2. **资源限制**: GPU 显存占用可配置
3. **权限控制**: 仅本地访问（127.0.0.1）
4. **日志记录**: 所有操作记录到日志

## 测试计划

1. **单元测试**: API 端点功能
2. **集成测试**: 启动/停止流程
3. **性能测试**: 多并发请求
4. **用户测试**: UI/UX 流畅度

## 文档更新

- [ ] 用户手册：如何使用本地推理引擎
- [ ] 开发文档：API 接口说明
- [ ] 故障排除：常见问题解决

## 未来扩展

1. **多 GPU 支持**: 在不同 GPU 上运行不同模型
2. **模型热切换**: 无需重启服务切换模型
3. **量化支持**: AWQ, GPTQ 自动检测和使用
4. **性能调优**: 自动调整 batch size, max_tokens 等参数
