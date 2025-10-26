# Locomo 数据集下载说明

## 背景

由于网络限制无法访问 Google Drive，我们改用 Hugging Face 托管数据集，并通过镜像站点下载。

## 使用方法

### 1. 快速下载（推荐）

如果数据集已上传到 Hugging Face，直接运行：

```bash
python locomo_download.py
```

脚本会自动使用 Hugging Face 镜像（`https://hf-mirror.com`）下载数据集。

### 2. 首次设置：上传数据集到 Hugging Face

如果你是第一次设置，需要先将数据集上传到 Hugging Face：

#### 步骤 1: 安装 Hugging Face CLI

```bash
pip install huggingface_hub
```

#### 步骤 2: 登录 Hugging Face

```bash
huggingface-cli login
```

输入你的 Hugging Face Token（在 https://huggingface.co/settings/tokens 获取）

#### 步骤 3: 上传数据集

```bash
# 进入数据目录
cd /path/to/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_stream/data/locomo

# 上传文件到 Hugging Face
huggingface-cli upload intellistream/locomo-benchmark locomo10.json locomo10.json --repo-type dataset
```

**注意**: 将 `intellistream/locomo-benchmark` 替换为你的 Hugging Face 用户名和仓库名。

#### 步骤 4: 更新脚本中的 repo_id

编辑 `locomo_download.py`，修改第 94 行：

```python
repo_id = "your-username/your-repo-name"  # 替换为你的仓库 ID
```

### 3. 使用不同的镜像站点

如果默认镜像站点 `hf-mirror.com` 访问有问题，可以尝试其他镜像：

在 `locomo_download.py` 中修改：

```python
download_from_huggingface(
    repo_id=repo_id,
    filename=filename,
    use_mirror=True,
    mirror_url="https://另一个镜像站点.com",  # 修改这里
)
```

常用 Hugging Face 镜像站点：

- `https://hf-mirror.com` （推荐）
- 其他镜像站点请自行搜索

### 4. 直接从 Hugging Face 下载（不使用镜像）

如果你的网络可以直接访问 Hugging Face：

```python
download_from_huggingface(
    repo_id=repo_id, filename=filename, use_mirror=False  # 关闭镜像
)
```

## 脚本说明

### `download_from_huggingface()` 函数

```python
def download_from_huggingface(
    repo_id,           # Hugging Face 仓库 ID，如 "username/repo-name"
    filename,          # 要下载的文件名，如 "locomo10.json"
    save_dir=None,     # 保存目录，默认为脚本所在目录
    use_mirror=True,   # 是否使用镜像
    mirror_url="https://hf-mirror.com",  # 镜像站点 URL
):
```

### `download_gdrive_file()` 函数（备用）

保留了原来的 Google Drive 下载功能，如果需要可以取消注释使用。

## 在代码中使用

下载完成后，可以直接使用 `LocomoDataLoader`：

```python
from locomo_dataloader import LocomoDataLoader

# 默认加载 locomo10.json
loader = LocomoDataLoader()

# 获取所有 sample_id
sample_ids = loader.get_sample_id()

# 获取单个样本
sample = loader.get_sample(sample_ids[0])

# 迭代 QA
for qa in loader.iter_qa(sample_ids[0]):
    print(qa)

# 迭代 session
for session in loader.iter_session(sample_ids[0]):
    print(session)
```

## 常见问题

### Q: 下载失败怎么办？

A: 请检查：

1. 网络连接是否正常
1. 镜像站点是否可访问（可以在浏览器中测试）
1. repo_id 是否正确
1. 文件名是否正确

### Q: 如何验证文件是否下载成功？

A: 运行测试脚本：

```bash
python locomo_dataloader.py
```

如果能正常输出 sample 信息，说明文件下载成功。

### Q: 可以下载其他文件吗？

A: 可以！只需修改 `filename` 参数：

```python
download_from_huggingface(
    repo_id="your-username/your-repo",
    filename="other_file.json",  # 修改这里
    use_mirror=True,
)
```

## 许可证

请遵守数据集的原始许可证。
