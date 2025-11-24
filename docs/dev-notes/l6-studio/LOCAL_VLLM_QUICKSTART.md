# SAGE Studio 本地推理使用快速指南

## 问题解答

### 1. 应该使用什么？
**答：使用 vLLM Server**
- `sage-llm` 是 SAGE 的封装，底层还是 vLLM
- 我们需要启动的是 **vLLM OpenAI-compatible Server**

### 2. 端口配置

**重要：避免端口冲突！**

| 服务 | 默认端口 | 推荐端口 | 说明 |
|------|---------|---------|------|
| Gateway | 8000 | 8000 | 保持不变 |
| vLLM | 8000 | **8001** | **避免冲突** |
| Studio Frontend | 4200 | 4200 | 保持不变 |
| Studio Backend | 8080 | 8080 | 保持不变 |

**检测优先级：**
- 代码会先检测 `8001` 端口（推荐）
- 然后检测 `8000` 端口（备选）

### 3. 启动本地 vLLM 服务

#### 方式 1: 使用 SAGE CLI（推荐）

```bash
# 启动 vLLM 服务（注意使用 8001 端口）
sage llm run Qwen/Qwen2.5-7B-Instruct --port 8001

# 或者使用其他模型
sage llm run Qwen/Qwen2.5-1.5B-Instruct --port 8001  # 低显存版本
```

#### 方式 2: 使用微调工具

```bash
# 启动微调后的模型
sage finetune serve <model-name> --port 8001
```

#### 方式 3: 直接使用 vLLM

```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --port 8001 \
    --gpu-memory-utilization 0.9
```

### 4. 使用流程

#### 场景 A: 完全自动（推荐）

```bash
# 1. 启动本地 vLLM（在一个终端）
sage llm run Qwen/Qwen2.5-7B-Instruct --port 8001

# 2. 启动 Studio（在另一个终端）
sage studio start

# 3. 打开浏览器，访问 Chat 页面
# 结果：自动检测到本地 vLLM，使用本地服务 ✅
```

#### 场景 B: 仅使用云端 API

```bash
# 1. 不启动本地 vLLM

# 2. 启动 Studio
sage studio start

# 3. 打开浏览器，访问 Chat 页面
# 结果：检测不到本地服务，自动降级到云端 API ☁️
```

#### 场景 C: 强制使用云端（即使有本地服务）

```bash
# .env 文件中添加
SAGE_FORCE_CLOUD_API=true

# 启动 Studio
sage studio start

# 结果：跳过本地检测，直接使用云端 API
```

### 5. 查看日志

#### Gateway 日志
```bash
tail -f ~/.sage/studio/chat/gateway.log

# 查看使用的是哪个服务：
# ✅ Using local vLLM: Qwen/Qwen2.5-7B-Instruct @ http://localhost:8001/v1
# 或
# ☁️  Using cloud API: qwen-turbo-2025-02-11 @ https://dashscope.aliyuncs.com/...
```

#### vLLM 日志
```bash
# 如果使用 sage llm run，日志会显示在终端
# 或查看日志文件
tail -f ~/.sage/llm_8001.log
```

### 6. 检查服务状态

```bash
# 检查 vLLM 是否运行
curl http://localhost:8001/health

# 查看可用模型
curl http://localhost:8001/v1/models

# 测试生成
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 50
  }'
```

### 7. 常见问题

#### Q: 端口 8001 被占用怎么办？
```bash
# 使用其他端口
sage llm run Qwen/Qwen2.5-7B-Instruct --port 8002

# 注意：需要修改代码中的检测端口列表
```

#### Q: GPU 显存不足？
```bash
# 使用较小的模型
sage llm run Qwen/Qwen2.5-1.5B-Instruct --port 8001

# 或降低 GPU 显存占用
sage llm run Qwen/Qwen2.5-7B-Instruct --port 8001 --gpu-util 0.7
```

#### Q: 如何停止本地 vLLM？
```bash
# 如果在前台运行，直接 Ctrl+C

# 如果后台运行
sage llm stop --port 8001
```

### 8. 性能对比

| 指标 | 本地 vLLM (RTX 3090) | 云端 API (DashScope) |
|------|---------------------|---------------------|
| 首 Token 延迟 | ~100ms | ~500ms |
| 生成速度 | ~50 tokens/s | ~30 tokens/s |
| 成本 | 免费（电费） | 按量收费 |
| 隐私 | ✅ 完全本地 | ⚠️ 数据上传 |
| 网络依赖 | ❌ 不需要 | ✅ 需要稳定网络 |

## 未来功能：Studio 一键启动

我已经创建了设计文档：`docs/dev-notes/l6-interfaces/studio/LOCAL_INFERENCE_ENGINE.md`

**计划功能：**
1. ✅ Studio 顶部显示本地引擎状态
2. 🔘 一键启动/停止本地 vLLM
3. 🎛️ Chat 页面选择 LLM 源（本地/云端/自动）
4. 📊 实时 GPU 监控
5. 📦 模型管理（下载、切换）

**实现优先级：**
- Phase 1 (1-2天): 状态显示 + 启动/停止
- Phase 2 (2-3天): LLM 源选择 + GPU 监控
- Phase 3 (3-5天): 模型管理 + 性能调优

**需要的技术：**
- 后端：FastAPI 端点管理 vLLM 进程
- 前端：Ant Design 组件（Button, Select, Statistic）
- 进程管理：subprocess + PID 文件
- 状态检测：HTTP health check + psutil

想要我开始实现吗？我可以先实现 Phase 1 的基础功能。
