# SAGE Studio 微调功能使用指南

## 新增功能概览

### 1. 使用 SAGE 官方文档作为训练语料 📚

**功能说明**：无需手动准备训练数据，一键使用 SAGE 官方文档进行微调。

**如何使用**：

1. 打开 Studio 微调面板
1. 在"训练数据集"区域选择 **"📚 使用 SAGE 官方文档"**
1. 系统会自动：
   - 从 GitHub 下载 `intellistream/SAGE-Pub/docs_src`
   - 将 Markdown 文档转换为 Alpaca 格式训练数据
   - 按标题分段生成 instruction-output 对
1. 等待准备完成，查看数据统计信息

**数据处理流程**：

```
GitHub Docs → 下载 docs_src/ → 解析 Markdown → 按标题分段
→ 生成 QA 对 → Alpaca JSON → 训练数据
```

**预期数据量**：

- 训练样本：100-300 条（取决于文档数量）
- 平均长度：500-1000 字符/样本
- 总 tokens：~50K-150K

### 2. 微调后的模型设为对话后端 🚀

**功能说明**：微调完成后，可以一键将模型设置为 Studio 的 LLM 后端，直接在 Chat 中使用。

**如何使用**：

1. 等待微调任务完成（状态：✅ 已完成）
1. 在任务列表中找到已完成的任务
1. 点击 **"设为后端"** 按钮
1. 确认弹窗后，模型将自动切换
1. 前往 Chat 面板测试微调后的模型

**后端切换流程**：

```
微调完成 → 注册到 vLLM Registry → 切换模型
→ 更新环境变量 → Chat/RAG 使用新模型
```

**技术细节**：

- 模型名称：`sage-finetuned-{task_id}`
- 自动配置 vLLM 参数：
  - `trust_remote_code=True`
  - `gpu_memory_utilization=0.8`
  - `max_model_len=2048`

### 3. 完整操作流程示例

#### 场景：使用 SAGE 文档微调 1.5B Coder 模型

```
步骤 1: 选择模型
  ✅ Qwen 2.5 Coder 1.5B (推荐，RTX 3060 适用)

步骤 2: 选择数据源
  📚 使用 SAGE 官方文档
  → 自动下载并准备（1-3 分钟）
  → 提示：共 150 条训练数据

步骤 3: 配置训练参数
  训练轮数: 3
  批量大小: 1
  学习率: 5e-5
  8-bit 量化: ✅ 开启

步骤 4: 开始训练
  点击"开始微调"
  → 任务创建成功
  → 状态：训练中 (2-4 小时)

步骤 5: 等待完成
  查看进度条
  → Epoch 1/3 (33%)
  → Epoch 2/3 (66%)
  → Epoch 3/3 (100%)
  → 状态：✅ 已完成

步骤 6: 设为后端
  点击"设为后端"
  → 确认切换
  → ✅ 已切换到微调模型: sage-finetuned-xxx
  → 提示：请在对话面板测试

步骤 7: 测试模型
  前往 Chat 面板
  输入：请介绍 SAGE 框架的核心架构
  → 模型使用微调后的知识回答
```

## API 接口说明

### 准备 SAGE 文档

```http
POST /api/finetune/prepare-sage-docs
Content-Type: application/json

{
  "force_refresh": false  // 可选，是否强制重新下载
}
```

**响应**：

```json
{
  "status": "success",
  "message": "SAGE 文档已准备完成",
  "data_file": "/home/user/.sage/studio_finetune/sage_docs/sage_docs_finetune_data.json",
  "stats": {
    "total_samples": 150,
    "total_chars": 120000,
    "avg_chars_per_sample": 800,
    "estimated_tokens": 30000
  }
}
```

### 设为对话后端

```http
POST /api/finetune/use-as-backend
Content-Type: application/json

{
  "task_id": "finetune-1234567890"
}
```

**响应**：

```json
{
  "status": "success",
  "message": "已切换到微调模型: sage-finetuned-1234567890",
  "model_name": "sage-finetuned-1234567890",
  "model_path": "/home/user/.sage/studio_finetune/outputs/finetune-1234567890"
}
```

## 前端 UI 更新

### 数据源选择（Radio Group）

```tsx
<Radio.Group>
  <Radio value="upload">
    📁 上传本地数据集
    支持 JSON/JSONL (Alpaca 格式)
  </Radio>
  <Radio value="sage-docs">
    📚 使用 SAGE 官方文档
    自动从 GitHub 下载并准备训练数据
  </Radio>
</Radio.Group>
```

### 任务操作按钮（已完成任务）

```tsx
<Space>
  <Button type="primary">使用此模型</Button>
  <Button type="default">设为后端</Button>  {/* 新增 */}
  <Button icon={<Download />}>下载</Button>
</Space>
```

## 技术实现细节

### 文档处理器 (`docs_processor.py`)

**核心类**: `SAGEDocsProcessor`

**主要方法**：

- `download_docs()`: 使用 git sparse checkout 下载 docs_src
- `convert_markdown_to_qa()`: 将 Markdown 转换为 QA 对
- `prepare_training_data()`: 完整流程（下载 → 转换 → 保存）
- `get_stats()`: 统计数据集信息

**转换策略**：

```python
# 按标题分段
sections = split_by_headers(md_content)

# 每个段落生成 QA 对
for title, content in sections:
    instruction = f"请介绍 SAGE 框架中关于 {title} 的内容"
    output = clean_markdown(content)
    qa_pairs.append({
        "instruction": instruction,
        "input": "",
        "output": output
    })
```

### 后端集成 (`api.py`)

**新增端点**：

1. `POST /api/finetune/prepare-sage-docs`

   - 调用 `SAGEDocsProcessor`
   - 返回数据文件路径和统计信息

1. `POST /api/finetune/use-as-backend`

   - 验证任务状态
   - 注册到 vLLM Registry
   - 切换模型并更新环境变量

### 前端集成 (`FinetunePanel.tsx`)

**新增状态/函数**：

- `handlePrepareSageDocs()`: 调用准备文档 API
- `handleUseAsBackend()`: 调用设为后端 API（带确认弹窗）

**UI 增强**：

- Radio Group 数据源选择
- "设为后端" 按钮（Modal 确认）

## 注意事项

### 1. 网络要求

- 需要能访问 GitHub (intellistream/SAGE-Pub)
- 国内用户建议配置 Git 代理
- 预计下载时间：1-3 分钟（取决于网速）

### 2. 存储空间

- 文档下载：~5-10 MB
- 训练数据：~1-2 MB (JSON)
- 微调模型：3-7 GB（取决于基础模型大小）

### 3. vLLM Registry 集成

- 确保 `sage.platform.llm.vllm_registry` 可用
- 模型注册需要 GPU 资源
- 切换模型会影响所有 Chat/RAG 功能

### 4. 数据质量

- SAGE 文档主要是技术说明文档
- 适合微调"SAGE 知识问答"场景
- 如需其他领域，建议上传自定义数据集

## 测试清单

- [ ] 选择"使用 SAGE 官方文档"并成功下载
- [ ] 查看准备完成后的统计信息
- [ ] 使用 Qwen 1.5B Coder 创建微调任务
- [ ] 等待训练完成（监控进度）
- [ ] 点击"设为后端"并确认
- [ ] 在 Chat 面板提问 SAGE 相关问题
- [ ] 验证回答质量是否提升
- [ ] 下载微调后的模型（tar.gz）

## 常见问题

**Q: 文档下载失败怎么办？** A: 检查网络连接，确保能访问 GitHub。可配置代理：

```bash
git config --global http.proxy http://127.0.0.1:7890
```

**Q: 准备数据后没有自动填充文件路径？** A: API 返回的 `data_file` 已自动设置到 `uploadedFile` 状态，直接提交表单即可。

**Q: 切换后端后 Chat 还是用旧模型？** A: 检查环境变量 `SAGE_STUDIO_LLM_MODEL`，确保 vLLM Registry 切换成功。

**Q: 训练数据太少效果不好？** A: SAGE 文档可能只有 100-200 条数据，建议：

1. 增加训练轮数（5-10 epochs）
1. 或补充上传自定义数据集

## 下一步计划

- [ ] 支持多数据源合并（SAGE 文档 + 自定义数据）
- [ ] 添加数据预览功能
- [ ] 支持更多文档格式（PDF, TXT, HTML）
- [ ] 集成数据增强（回译、改写等）
- [ ] 添加模型评估指标（perplexity, BLEU等）
