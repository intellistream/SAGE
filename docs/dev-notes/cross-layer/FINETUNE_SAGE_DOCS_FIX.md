# 修复：准备 SAGE 文档失败

## 问题描述

用户在 Finetune 面板选择"📚 使用 SAGE 官方文档"时，提示"准备文档失败"。

## 根本原因

**CORS 配置缺失** ❌

后端 API (`api.py`) 的 CORS 中间件配置中没有包含前端实际运行的端口 `http://localhost:4200`，导致浏览器阻止了跨域请求。

```python
# 原配置（缺少 4200 端口）
allow_origins=[
    "http://localhost:5173",  # Vite 开发服务器
    "http://localhost:4173",  # Vite preview
    "http://0.0.0.0:5173",
    "http://0.0.0.0:4173",
]
```

## 修复方案

### 1. 添加 CORS 端口配置 ✅

**文件**: `packages/sage-studio/src/sage/studio/config/backend/api.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:4200",  # ← 新增 Studio 前端端口
        "http://0.0.0.0:5173",
        "http://0.0.0.0:4173",
        "http://0.0.0.0:4200",    # ← 新增
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. 改进前端错误处理 ✅

**文件**: `packages/sage-studio/src/sage/studio/frontend/src/components/FinetunePanel.tsx`

**改进点**：
1. 添加详细的错误日志到控制台
2. 显示具体错误消息而不是通用错误
3. 添加数据准备成功的视觉反馈

```typescript
const handlePrepareSageDocs = async () => {
    const hide = message.loading('正在下载 SAGE 文档并准备训练数据...', 0)
    try {
        const response = await fetch('http://localhost:8080/api/finetune/prepare-sage-docs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),  // ← 添加空 body
        })

        if (response.ok) {
            const data = await response.json()
            setUploadedFile(data.data_file)
            message.success(`SAGE 文档已准备完成！共 ${data.stats.total_samples} 条训练数据`)
        } else {
            const error = await response.json().catch(() => ({ detail: response.statusText }))
            message.error(error.detail || '准备文档失败')
            console.error('Prepare docs error:', error)  // ← 详细日志
        }
    } catch (error) {
        console.error('Prepare docs exception:', error)  // ← 捕获异常日志
        message.error(`准备文档失败: ${error instanceof Error ? error.message : '未知错误'}`)
    } finally {
        hide()
    }
}
```

### 3. 添加数据状态指示器 ✅

在上传区域显示已准备的数据文件名：

```tsx
{uploadedFile && (
    <Text type="success" style={{ fontSize: 12 }}>
        ✅ 数据已准备: {uploadedFile.split('/').pop()}
    </Text>
)}
```

## 验证测试

### 后端测试 ✅

```bash
# 直接测试 API 端点
curl -X POST http://localhost:8080/api/finetune/prepare-sage-docs \
  -H "Content-Type: application/json" \
  -d '{}'

# 响应成功
{
  "status": "success",
  "message": "SAGE 文档已准备完成",
  "data_file": "/home/shuhao/.sage/studio_finetune/sage_docs/sage_docs_finetune_data.json",
  "stats": {...}
}
```

### Python 模块测试 ✅

```bash
python3 -c "
from sage.studio.services.docs_processor import get_docs_processor
processor = get_docs_processor()
result = processor.prepare_training_data(force_refresh=False)
print(f'✅ Success: {result}')
"

# 输出
✅ Success: /home/shuhao/.sage/studio_finetune/sage_docs/sage_docs_finetune_data.json
```

## 完整修复文件清单

1. ✅ `packages/sage-studio/src/sage/studio/config/backend/api.py`
   - 添加 4200 端口到 CORS 配置

2. ✅ `packages/sage-studio/src/sage/studio/frontend/src/components/FinetunePanel.tsx`
   - 改进 `handlePrepareSageDocs()` 错误处理
   - 添加控制台日志
   - 显示详细错误消息
   - 添加数据准备成功提示
   - Radio onChange 使用 async/await

## 使用说明

修复后的使用流程：

1. **打开 Finetune 面板**
2. **选择数据源**: 点击 "📚 使用 SAGE 官方文档"
3. **等待准备**:
   - 显示加载提示："正在下载 SAGE 文档并准备训练数据..."
   - 首次下载需要 1-3 分钟
4. **查看成功提示**: "✅ SAGE 文档已准备完成！共 XXX 条训练数据"
5. **查看文件名**: 显示 "✅ 数据已准备: sage_docs_finetune_data.json"
6. **继续微调**: 选择模型和参数，点击"开始微调"

## 故障排查

如果仍然失败，检查：

1. **浏览器控制台** (F12)：
   - 查看是否有 CORS 错误
   - 查看详细错误日志

2. **网络连接**：
   - 确保能访问 GitHub
   - 检查代理设置

3. **磁盘空间**：
   - 确保 `~/.sage/studio_finetune/` 有足够空间

4. **权限问题**：
   - 检查目录写入权限

## 相关文件位置

```
packages/
├── sage-studio/
    ├── src/sage/studio/
        ├── config/backend/
        │   └── api.py                     ← CORS 配置
        ├── frontend/src/components/
        │   └── FinetunePanel.tsx          ← UI 和错误处理
        └── services/
            └── docs_processor.py          ← 文档下载和处理
```

## 已应用更改

```bash
# 重启 Studio 以应用更改
sage studio restart

# 访问地址
http://localhost:4200
```

现在功能应该正常工作了！🎉
