# SAGE 工具脚本

本目录包含SAGE开发和演示相关的工具脚本。

## 脚本说明

### 演示脚本
- `demo_llm_autoconfig.py` - 完整演示SAGE LLM自动配置功能 (#826)
- `mock_vllm_server.py` - Mock vLLM服务器，用于测试LLM自动配置功能

### 系统工具脚本
- `common_utils.sh` - 通用工具函数
- `config.sh` - 配置管理脚本
- `logging.sh` - 日志工具
- `python_bridge.sh` - Python桥接脚本

## 使用方法

### LLM自动配置演示
```bash
cd /home/shuhao/SAGE
python tools/utils/demo_llm_autoconfig.py
```

### Mock vLLM服务器
```bash
python tools/utils/mock_vllm_server.py
```

## 注意事项

演示脚本主要用于功能展示和测试，请根据实际需求调整配置。