# SAGE LLM服务配置自动化解决方案

## 问题描述 (Issue #826)

用户反馈：
> "Ollama部署成llm服务之后，需要将config中generator的url和model name替换一下你部署的服务。这一点比较麻烦，你有没有什么好办法，能够让sage 命令自动化去做这件事，简化用户操作。"

核心问题：
- 用户部署Ollama/vLLM服务后，需要手动修改配置文件
- 需要手动查找服务URL、端口和可用模型
- 配置过程容易出错，用户体验不佳
- 不仅是Ollama，还需要支持vLLM等其他服务

## 解决方案

### 1. 核心功能实现

#### 1.1 LLM服务检测模块 (`llm_detection.py`)
```python
# 自动检测本地LLM服务
def detect_ollama() -> Optional[LLMServiceInfo]:
    """检测Ollama服务 (默认端口11434)"""

def detect_vllm() -> Optional[LLMServiceInfo]:  
    """检测vLLM服务 (默认端口8000)"""

def detect_all_services() -> List[LLMServiceInfo]:
    """检测所有支持的服务"""
```

特性：
- HTTP探测服务可用性
- 自动获取模型列表
- 支持SSL和超时处理
- 容错机制，避免因网络问题导致检测失败

#### 1.2 CLI命令 (`config.py`)
```bash
# 新增CLI命令
sage config llm auto [OPTIONS]
```

命令选项：
- `--config-path, -c`: 指定配置文件路径
- `--prefer`: 优先检测的服务类型 (ollama/vllm)
- `--model-name, -m`: 指定模型名称
- `--section, -s`: 目标配置节
- `--yes, -y`: 自动模式，无需交互确认
- `--backup/--no-backup`: 是否创建备份

#### 1.3 安全的配置更新
- 自动创建配置文件备份
- YAML格式解析和写入
- 保留原有配置结构和注释
- 仅更新必要的generator配置项

### 2. 支持的服务类型

| 服务类型 | 默认端口 | API端点 | 检测方式 |
|---------|----------|---------|----------|
| Ollama | 11434 | `/api/tags` | HTTP GET |
| vLLM | 8000 | `/v1/models` | HTTP GET |

### 3. 使用示例

#### 3.1 交互式模式
```bash
# 自动检测并提供选择菜单
sage config llm auto --config-path config/config.yaml
```

输出示例：
```
检测到以下LLM服务：
1. Ollama (http://localhost:11434)
   模型: llama2, codellama, mistral
2. vLLM (http://localhost:8000) 
   模型: microsoft/DialoGPT-medium, gpt2

请选择要使用的服务 [1]: 1
请选择模型 [llama2]: llama2
✅ 配置已更新
✅ 备份已创建: config/config.yaml.backup
```

#### 3.2 全自动模式
```bash
# 无需交互，自动选择第一个检测到的服务
sage config llm auto --config-path config/config.yaml --yes
```

#### 3.3 指定服务类型
```bash
# 优先检测Ollama服务
sage config llm auto --prefer ollama --yes
```

#### 3.4 指定模型
```bash
# 指定使用特定模型
sage config llm auto --model-name llama2 --yes
```

### 4. 配置文件更新示例

#### 更新前:
```yaml
generator:
  type: remote
  url: "http://old-api-server:8080/v1/chat/completions"
  model: "old-model"
  api_key: "${OPENAI_API_KEY}"
  temperature: 0.7
  max_tokens: 2000
```

#### 更新后:
```yaml
generator:
  type: remote
  url: "http://localhost:11434/v1/chat/completions"  # 自动更新
  model: "llama2"                                     # 自动更新
  api_key: "${OPENAI_API_KEY}"                       # 保持不变
  temperature: 0.7                                    # 保持不变
  max_tokens: 2000                                    # 保持不变
```

### 5. 技术实现细节

#### 5.1 依赖解决
- 解决了NumPy版本冲突 (2.3.3 → 2.2.6)
- 解决了OpenAI版本冲突 (1.90.0 → 1.109.1)
- 确保vLLM和Numba兼容性

#### 5.2 错误处理
- 网络连接超时处理
- SSL证书验证
- JSON解析异常处理
- 配置文件读写错误处理

#### 5.3 测试覆盖
```python
# 完整的测试套件
test_auto_updates_generator_remote()      # 基本更新功能
test_auto_updates_specific_section()      # 指定配置节
test_auto_handles_missing_services()      # 无服务时的处理
```

### 6. 用户体验改进

#### 6.1 操作简化
- **之前**: 5个手动步骤（部署→查询→编辑→更新→重启）
- **现在**: 1个命令 (`sage config llm auto --yes`)

#### 6.2 错误减少
- 自动验证服务可用性
- 自动验证模型名称
- 防止无效URL和端口配置

#### 6.3 灵活性
- 支持交互式和自动模式
- 支持多种服务类型
- 可指定特定模型和配置节

### 7. 部署状态

✅ **已完成**:
- LLM服务检测功能
- CLI命令实现
- 配置自动更新
- 完整测试覆盖
- 依赖问题解决
- 文档和示例

✅ **测试验证**:
- 所有单元测试通过
- 功能演示完成
- 兼容性确认

## 总结

本解决方案成功实现了Issue #826要求的LLM服务配置自动化功能：

1. **自动检测**: 支持Ollama和vLLM服务的自动发现
2. **一键配置**: 通过`sage config llm auto`命令实现一键配置更新
3. **用户友好**: 提供交互式和自动化两种模式
4. **安全可靠**: 自动备份配置文件，容错处理
5. **扩展性强**: 易于添加对新LLM服务的支持

**用户现在只需一个命令即可完成之前需要手动操作的复杂配置过程，大大提升了SAGE框架的易用性。**