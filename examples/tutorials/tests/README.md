# Tutorials Tests

本目录包含 tutorials 中示例的测试文件。

## 说明

⚠️ **重要**：这些是测试文件，不是示例文件。

- 示例文件位于各层级目录中（L1-L6, tools）
- 测试文件用于验证示例的正确性

## 测试文件列表

- `test_new_templates.py` - 模板系统测试
- `test_real_llm.py` - LLM 集成测试
- `test_template_matching.py` - 模板匹配测试

## 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行单个测试
pytest tests/test_new_templates.py
```
