from datasets import load_dataset
from sage.kernel.api.function.batch_function import BatchFunction


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
        except StopIteration:
            self.logger.info(f"HF dataset batch processing completed for: {self.hf_name}")
            self._dataset_exhausted = True
            return None
