# VLLM 本地服务说明文档

## 概述
`vllm_local_serve.sh` 是一个用于启动 VLLM 本地推理服务的脚本，支持多种语言模型的自动下载和部署。

## 功能特性
- ✅ 自动检测和安装 VLLM
- ✅ 智能模型检测和下载提示
- ✅ 自动设置 HuggingFace 镜像（中国用户友好）
- ✅ 支持交互式和自动确认模式
- ✅ 模型缓存管理
- ✅ 详细的错误处理和用户提示

## 使用方法

### 基本用法
```bash
# 使用默认模型（microsoft/DialoGPT-small）
./tools/vllm/vllm_local_serve.sh

# 使用指定模型
./tools/vllm/vllm_local_serve.sh microsoft/DialoGPT-medium

# 自动确认模式（无需交互）
./tools/vllm/vllm_local_serve.sh --yes

# 自动确认 + 指定模型
./tools/vllm/vllm_local_serve.sh --yes microsoft/DialoGPT-large
```

### 命令行选项
- `--yes, -y`: 自动确认所有提示，适合脚本化使用
- `--help, -h`: 显示帮助信息

## 推荐模型

### 按大小排序
| 模型名称 | 大小 | 用途 | 推荐场景 |
|---------|------|------|----------|
| `microsoft/DialoGPT-small` | ~500MB | 轻量测试 | 快速验证、开发测试 |
| `microsoft/DialoGPT-medium` | ~1.5GB | 开发使用 | 日常开发、原型设计 |
| `microsoft/DialoGPT-large` | ~3GB | 更好效果 | 演示、小规模生产 |
| `meta-llama/Llama-2-7b-chat-hf` | ~14GB | 专业应用 | 生产环境、高质量推理 |

### 选择建议
- **首次使用**: 建议使用 `microsoft/DialoGPT-small` 进行测试
- **开发阶段**: 使用 `microsoft/DialoGPT-medium` 平衡性能和资源
- **生产环境**: 根据需求选择更大的模型

## 网络配置

### 自动镜像设置
脚本会自动检测网络连接：
- 如果可以访问 HuggingFace 官网，直接使用官方源
- 如果无法访问，自动切换到 `https://hf-mirror.com` 镜像

### 手动设置镜像
如果需要手动设置镜像：
```bash
export HF_ENDPOINT=https://hf-mirror.com
./tools/vllm/vllm_local_serve.sh
```

## 故障排除

### 常见问题

#### 1. VLLM 未安装
```
[ERROR] vllm 安装失败，请检查 conda 环境
```
**解决方案**: 重新运行安装脚本或手动安装：
```bash
pip install vllm
```

#### 2. 模型下载失败
```
[WARNING] 模型下载失败，请检查网络或考虑使用其他模型
```
**解决方案**:
- 检查网络连接
- 尝试使用更小的模型
- 使用 `--yes` 参数跳过交互

#### 3. 显存不足
```
CUDA out of memory
```
**解决方案**:
- 使用更小的模型
- 减少 batch size
- 关闭其他 GPU 程序

#### 4. 启动卡住
如果脚本在交互确认处卡住：
```
是否继续启动服务？模型将在启动时自动下载 [y/N]:
```
**解决方案**:
- 输入 `y` 并按回车继续
- 或使用 `--yes` 参数跳过交互：
  ```bash
  ./tools/vllm/vllm_local_serve.sh --yes
  ```

## 服务信息

### 默认配置
- **服务地址**: `http://localhost:8000`
- **API Key**: `token-abc123`
- **数据类型**: auto（自动检测）

### API 使用示例
```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="token-abc123"
)

response = client.chat.completions.create(
    model="microsoft/DialoGPT-small",  # 使用启动的模型名称
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

## 日志和调试

### 查看日志
脚本会输出详细的运行信息，包括：
- 网络连接状态
- 模型检测结果
- 下载进度
- 服务启动状态

### 调试模式
设置环境变量启用详细日志：
```bash
export VLLM_LOGGING_LEVEL=DEBUG
./tools/vllm/vllm_local_serve.sh
```

## 进阶配置

### 自定义启动参数
可以修改脚本最后一行来自定义 VLLM 参数：
```bash
# 默认
vllm serve "$MODEL" --dtype auto --api-key token-abc123

# 自定义示例
vllm serve "$MODEL" --dtype auto --api-key token-abc123 --max-model-len 2048 --gpu-memory-utilization 0.8
```

### 环境变量
- `HF_ENDPOINT`: HuggingFace 镜像地址
- `HF_HOME`: 模型缓存目录
- `CUDA_VISIBLE_DEVICES`: 指定 GPU 设备

## 最佳实践

1. **首次使用**: 先测试小模型确保环境正常
2. **生产部署**: 使用 `--yes` 参数避免交互
3. **资源管理**: 根据硬件配置选择合适的模型
4. **网络优化**: 在网络不佳时使用镜像源
5. **监控**: 定期检查服务状态和资源使用

## 相关文件

- `./tools/vllm/vllm_local_serve.sh`: 主启动脚本
- `./tools/vllm/verify_vllm_fix.sh`: VLLM 安装验证脚本
- `./tools/install/installation_table/vllm_installer.sh`: VLLM 安装器
