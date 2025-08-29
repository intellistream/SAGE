import json
import os
from sage.core.api.function.batch_function import BatchFunction

try:
    from datasets import load_dataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False


class HFDatasetBatch(BatchFunction):
    """
    HuggingFace数据集批处理函数

    从HuggingFace数据集中批量读取数据，支持流式处理。
    当数据集处理完成时返回None来停止批处理。

    Input: None (直接从HF数据集读取)
    Output: 包含query和references的字典对象

    Attributes:
        config: 配置字典，包含数据集设置
        hf_name: HuggingFace数据集名称
        hf_config: 数据集配置名称
        hf_split: 数据集分割（train/validation/test等）
        _iter: 数据集迭代器
    """

    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        if not HAS_DATASETS:
            raise ImportError("datasets library is required for HFDatasetBatch. Install with: pip install datasets")
        self.config = config
        self.hf_name = config["hf_dataset_name"]
        self.hf_config = config.get("hf_dataset_config")
        self.hf_split = config.get("hf_split", "train")
        self._iter = None
        self._dataset_exhausted = False

    def _build_iter(self):
        """构建数据集迭代器"""
        ds = load_dataset(self.hf_name, self.hf_config, split=self.hf_split, streaming=True)
        for ex in ds:
            yield {
                "query": ex.get("question", ""),
                "references": ex.get("golden_answers") or []
            }

    def execute(self):
        """
        执行批处理函数逻辑

        Returns:
            dict: 包含query和references的数据字典，数据集结束时返回None
        """
        if self._dataset_exhausted:
            return None

        if self._iter is None:
            self.logger.debug(f"Initializing HF dataset batch source: {self.hf_name}")
            self._iter = self._build_iter()

        try:
            data = next(self._iter)
            self.logger.debug(f"Yielding batch data: {data}")
            return data
            time.sleep(1)
        except StopIteration:
            self.logger.info(f"HF dataset batch processing completed for: {self.hf_name}")
            self._dataset_exhausted = True
            return None


class JSONLBatch(BatchFunction):
    """
    JSONL文件批处理函数

    逐行读取JSONL文件中的数据，支持流式处理。
    当文件处理完成时返回None来停止批处理。

    Input: None (直接从JSONL文件读取)
    Output: 包含query和其他字段的字典对象

    Attributes:
        config: 配置字典，包含文件路径设置
        file_path: JSONL文件路径
        _file_handle: 文件句柄
        _file_exhausted: 文件是否已读取完毕
    """

    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.file_path = config["data_path"]
        self._file_handle = None
        self._file_exhausted = False

    def _open_file(self):
        """打开JSONL文件"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"JSONL file not found: {self.file_path}")
        
        self._file_handle = open(self.file_path, 'r', encoding='utf-8')
        self.logger.debug(f"Opened JSONL file: {self.file_path}")

    def execute(self):
        """
        执行批处理函数逻辑

        Returns:
            dict: 包含query和其他字段的数据字典，文件结束时返回None
        """
        if self._file_exhausted:
            return None

        if self._file_handle is None:
            self.logger.debug(f"Initializing JSONL batch source: {self.file_path}")
            self._open_file()

        try:
            line = self._file_handle.readline()
            if not line:
                # 文件读取完毕
                self.logger.info(f"JSONL file batch processing completed for: {self.file_path}")
                self._file_handle.close()
                self._file_exhausted = True
                return None
            
            # 解析JSON行
            line = line.strip()
            if line:
                data = json.loads(line)
                # 如果data包含query字段，直接返回query字符串
                if 'query' in data:
                    query_text = data['query']
                    self.logger.debug(f"Yielding JSONL query: {query_text}")
                    return query_text
                else:
                    # 否则返回完整数据
                    self.logger.debug(f"Yielding JSONL data: {data}")
                    return data
            else:
                # 空行，继续读取下一行
                return self.execute()
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON line: {line}, error: {e}")
            # 跳过错误行，继续处理
            return self.execute()
        except Exception as e:
            self.logger.error(f"Error reading JSONL file: {e}")
            if self._file_handle:
                self._file_handle.close()
            self._file_exhausted = True
            return None

    def __del__(self):
        """析构函数，确保文件句柄被正确关闭"""
        if hasattr(self, '_file_handle') and self._file_handle:
            self._file_handle.close()
