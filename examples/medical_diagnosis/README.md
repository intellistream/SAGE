# 医疗诊断应用 - 快速入门

这是医疗诊断应用的快速入门示例目录。

## ⚠️ 重要说明

**完整应用已迁移到:**
```
packages/sage-libs/src/sage/libs/applications/medical_diagnosis/
```

本目录仅包含快速演示示例，用于：
- 5分钟快速了解系统功能
- 教学和文档演示
- 快速验证环境配置

## 🚀 快速开始

### 运行快速演示（无需数据集）

```bash
# 在项目根目录执行
python examples/medical_diagnosis/quick_start.py
```

这将展示：
- 系统初始化流程
- 模拟诊断过程
- 基本使用方法

### 查看功能特性

```bash
python examples/medical_diagnosis/quick_start.py --show-features
```

## 📚 完整应用

如需使用完整功能，请参考完整应用：

### 1. 安装依赖

```bash
pip install sage-libs[medical]
```

或手动安装：
```bash
pip install huggingface_hub datasets pillow scikit-learn
```

### 2. 准备数据集

```bash
cd packages/sage-libs/src/sage/libs/applications/medical_diagnosis/
./setup_data.sh
```

### 3. 运行完整测试

```bash
# 单病例测试
python -m sage.libs.applications.medical_diagnosis.test_diagnosis --mode single

# 批量测试
python -m sage.libs.applications.medical_diagnosis.test_diagnosis --mode batch
```

### 4. 交互式使用

```bash
python -m sage.libs.applications.medical_diagnosis.run_diagnosis --interactive
```

## 📖 完整文档

请访问完整应用目录获取详细文档：
- 📁 [完整应用代码](../../packages/sage-libs/src/sage/libs/applications/medical_diagnosis/)
- 📄 [详细README](../../packages/sage-libs/src/sage/libs/applications/medical_diagnosis/README.md)
- 🔧 [配置说明](../../packages/sage-libs/src/sage/libs/applications/medical_diagnosis/config/)
- 🧪 [测试指南](../../packages/sage-libs/src/sage/libs/applications/medical_diagnosis/test_diagnosis.py)

## 🎯 学习路径

1. **初学者**: 运行本目录的 `quick_start.py`
2. **进阶**: 查看完整应用的 Agent 实现
3. **高级**: 修改配置和扩展功能
4. **专家**: 贡献新的医疗诊断模型

## 💡 示例 vs 应用

### Examples (本目录)
- ✅ 简单快速（<200行代码）
- ✅ 教学目的
- ✅ 无需数据准备
- ✅ 5分钟运行完成

### Applications (完整应用)
- ✅ 生产级代码（>1000行）
- ✅ 完整架构（Agents + Tools + Pipelines）
- ✅ 真实数据集
- ✅ 完整测试覆盖
- ✅ 可独立安装使用

## 🔗 相关链接

- [SAGE Framework](https://github.com/intellistream/SAGE)
- [Applications Organization Strategy](../../docs/dev-notes/APPLICATION_ORGANIZATION_STRATEGY.md)
- [Lumbar Spine MRI Dataset](https://huggingface.co/datasets/UniDataPro/lumbar-spine-mri)
