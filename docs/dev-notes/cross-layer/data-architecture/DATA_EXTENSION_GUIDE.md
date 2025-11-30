# SAGE Data Extension Guide - 如何扩展数据架构

本指南说明如何在 SAGE 两层数据架构中添加新数据集和定义新用途。

---

## 场景 1: 添加新数据集到 Sources 层

假设你有一个新的数据集 `my_dataset`（例如，用于图像分类的自定义数据）。

### Step 1: 创建数据集目录

```bash
cd packages/sage-benchmark/src/sage/data/sources
mkdir my_dataset
cd my_dataset
```

### Step 2: 组织数据文件

```text
my_dataset/
├── dataset.yaml      # 元数据（必需）
├── __init__.py       # 导出 Loader
├── loader.py         # 数据加载器
├── raw/              # 原始数据（可选）
│   ├── train.csv
│   └── test.csv
├── preprocessed/     # 预处理数据（可选）
└── README.md         # 数据集文档
```

### Step 3: 编写 `dataset.yaml`

```yaml
# dataset.yaml
name: "my_dataset"
description: "Custom image classification dataset for XXX research"
type: "image"
format: "csv+jpeg"
maintainer: "your-github-username"
tags: ["image-classification", "custom", "experimental"]
size: "~2.5GB"
license: "CC BY 4.0"
version: "1.0.0"
source_url: "https://example.com/my_dataset"  # 可选
citation: |  # 可选
  @article{author2025my_dataset,
    title={My Dataset},
    author={Your Name},
    year={2025}
  }
```

### Step 4: 实现数据加载器

```python
# loader.py
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

class MyDatasetLoader:
    """Loader for My Custom Dataset."""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "raw"
        self.data_dir = Path(data_dir)

    def load_train(self) -> pd.DataFrame:
        """Load training data."""
        return pd.read_csv(self.data_dir / "train.csv")

    def load_test(self) -> pd.DataFrame:
        """Load test data."""
        return pd.read_csv(self.data_dir / "test.csv")

    def get_image_path(self, image_id: str) -> Path:
        """Get path to an image file."""
        return self.data_dir / "images" / f"{image_id}.jpg"
```

### Step 5: 导出接口

```python
# __init__.py
"""
My Custom Dataset

Usage:
    from sage.data.sources.my_dataset import MyDatasetLoader

    loader = MyDatasetLoader()
    train_data = loader.load_train()
"""

from .loader import MyDatasetLoader

__all__ = ["MyDatasetLoader"]
```

### Step 6: 添加文档

```markdown
# My Dataset

## Overview
Brief description of your dataset.

## Statistics
- Training samples: 10,000
- Test samples: 2,000
- Classes: 10
- Image size: 224x224

## Usage
\`\`\`python
from sage.data import DataManager

# Direct access
loader = DataManager.get_source("my_dataset").MyDatasetLoader()
train = loader.load_train()

# Via usage profile (if registered)
my_usage = DataManager.get_usage("my_experiment")
loader = my_usage.load("my_dataset")
\`\`\`

## Citation
If you use this dataset, please cite...
```

---

## 场景 2: 定义新用途 (Usage Profile)

假设你正在做一个新的实验项目 `multimodal_fusion`，需要使用多个数据集。

### Step 1: 创建用途目录

```bash
cd packages/sage-benchmark/src/sage/data/usages
mkdir multimodal_fusion
cd multimodal_fusion
```

### Step 2: 配置用途文件

```yaml
# config.yaml
description: "Multimodal fusion experiments combining text, image, and video"
maintainer: "your-name"
datasets:
  # 文本数据
  text_corpus: "qa_base"
  qa_pairs: "mmlu"

  # 图像数据
  images: "my_dataset"
  visual_features: "mnist"

  # 视频数据（假设已存在）
  videos: "video_dataset"

  # 向量数据（用于相似度搜索）
  embeddings: "sift"

# 可选：定义该用途特定的配置
preprocessing:
  text_max_length: 512
  image_size: [224, 224]
  batch_size: 32
```

### Step 3: (可选) 创建用途特定的工具

```python
# __init__.py
"""
Multimodal Fusion Usage Profile

Provides convenient access to datasets for multimodal fusion experiments.
"""

from sage.data import DataManager

class MultimodalDataHelper:
    """Helper class for multimodal fusion experiments."""

    def __init__(self):
        self.profile = DataManager.get_usage("multimodal_fusion")

    def load_text_data(self):
        """Load all text-related datasets."""
        return {
            "corpus": self.profile.load("text_corpus"),
            "qa": self.profile.load("qa_pairs")
        }

    def load_image_data(self):
        """Load all image-related datasets."""
        return {
            "images": self.profile.load("images"),
            "features": self.profile.load("visual_features")
        }

    def get_combined_loader(self, modalities: list):
        """Get loaders for specified modalities."""
        loaders = {}
        for modality in modalities:
            if modality in ["text", "qa"]:
                loaders.update(self.load_text_data())
            elif modality in ["image", "visual"]:
                loaders.update(self.load_image_data())
        return loaders

# Convenience exports
__all__ = ["MultimodalDataHelper"]
```

### Step 4: 使用新的 Usage Profile

```python
# 在你的实验代码中
from sage.data import DataManager

# 方法 1: 直接使用
profile = DataManager.get_usage("multimodal_fusion")
text_loader = profile.load("text_corpus")
image_loader = profile.load("images")

# 方法 2: 使用 Helper
from sage.data.usages.multimodal_fusion import MultimodalDataHelper

helper = MultimodalDataHelper()
text_data = helper.load_text_data()
image_data = helper.load_image_data()
```

---

## 场景 3: 临时实验数据（不提交到主仓库）

如果你的数据是临时的或私有的，可以使用本地扩展：

### 方法 A: 本地 Sources

```bash
# 在你的工作目录
mkdir -p my_local_data/sources/private_dataset
```

```python
# 在代码中指定自定义数据根目录
from sage.data import DataManager

manager = DataManager(data_root="/path/to/my_local_data")
loader = manager.get_source("private_dataset")
```

### 方法 B: 环境变量

```bash
export SAGE_DATA_ROOT=/path/to/my_local_data
```

```python
# 自动使用环境变量指定的路径
from sage.data import DataManager

manager = DataManager.get_instance()
```

---

## 场景 4: 与团队共享自定义 Usage

假设你的团队有一个共享的实验配置，但不想合并到主分支：

### Step 1: 创建独立的配置文件

```yaml
# team_experiments/vision_project.yaml
description: "Team vision project experiments"
datasets:
  custom_images: "team_image_dataset"
  pretrained_features: "sift"
  labels: "my_dataset"
```

### Step 2: 动态加载

```python
from sage.data import DataManager
import yaml

# 加载团队配置
with open("team_experiments/vision_project.yaml") as f:
    config = yaml.safe_load(f)

# 手动创建 UsageProfile
manager = DataManager.get_instance()
# 使用自定义逻辑访问数据集
```

---

## 最佳实践

### ✅ DO:
- 为每个数据集编写清晰的 `README.md`
- 在 `dataset.yaml` 中包含完整的元数据
- 使用语义化的版本号
- 为大文件使用 Git LFS
- 添加单元测试验证数据加载器

### ❌ DON'T:
- 不要在 `sources/` 中混合多个数据集
- 不要在 `usages/` 中复制数据（使用引用）
- 不要硬编码路径
- 不要提交大型二进制文件到 Git（使用 LFS 或外部存储）

---

## 测试你的扩展

```python
# test_my_extension.py
import pytest
from sage.data import DataManager

def test_my_dataset_loads():
    """Test that custom dataset loads correctly."""
    manager = DataManager.get_instance()
    loader_module = manager.get_source("my_dataset")
    loader = loader_module.MyDatasetLoader()

    train = loader.load_train()
    assert len(train) > 0

def test_my_usage_profile():
    """Test custom usage profile."""
    manager = DataManager.get_instance()
    profile = manager.get_usage("multimodal_fusion")

    assert "text_corpus" in profile.list_datasets()
    assert "images" in profile.list_datasets()
```

---

## 提交指南

如果要将你的扩展合并到主仓库：

1. Fork 仓库并创建特性分支
2. 添加数据集到 `sources/`
3. 更新相关的 `usages/` 配置
4. 添加测试和文档
5. 提交 Pull Request，说明：
   - 数据集的用途
   - 数据来源和许可
   - 使用示例
   - 测试覆盖

---

## 需要帮助？

- 查看 `docs/dev-notes/data_architecture_redesign.md` 了解架构设计
- 查看现有数据集（如 `sources/bbh/`）作为参考
- 在 GitHub Issues 中提问
