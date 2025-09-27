# SAGE 诊断工具

本目录包含用于诊断和调试SAGE系统问题的工具脚本。

## 脚本说明

### 调试脚本
- `analyze_mock_similarity.py` - 分析MockEmbedder生成的向量相似度
- `debug_embedding_detection.py` - 调试embedding模型检测逻辑  
- `debug_neuromem_similarity.py` - 调试neuromem相似度分数
- `debug_raw_similarity.py` - 调试原始相似度分数
- `debug_sage_flow_import.py` - 诊断SAGE Flow导入问题的脚本
- `test_mock_embedder.py` - 测试MockEmbedder场景

### 系统检查脚本  
- `check_compatibility.py` - 检查系统兼容性
- `check_packages_status.sh` - 检查包状态
- `diagnose_sage.py` - 综合诊断SAGE系统

## 使用方法

从SAGE根目录运行：
```bash
python tools/diagnostics/script_name.py
```

## 注意事项

这些脚本主要用于开发和调试目的，在生产环境中请谨慎使用。