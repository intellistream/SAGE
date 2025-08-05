from sage.api.function.map_function import MapFunction
from sage.plugins.longrefiner_fn.longrefiner.refiner import LongRefiner
import os
import time
import json

class LongRefinerAdapter(MapFunction):
    def __init__(self, config: dict, enable_profile=False, ctx=None):
        super().__init__(config=config, ctx=ctx)
        required = [
            "base_model_path",
            "query_analysis_module_lora_path",
            "doc_structuring_module_lora_path",
            "global_selection_module_lora_path",
            "score_model_name",
            "score_model_path",
            "max_model_len",
            "budget",
        ]
        missing = [k for k in required if k not in config]
        if missing:
            raise RuntimeError(f"[LongRefinerAdapter] 缺少配置字段: {missing}")
        self.cfg = config
        self.enable_profile = enable_profile
        self.refiner: LongRefiner | None = None

        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            if hasattr(self.ctx, 'env_base_dir') and self.ctx.env_base_dir:
                self.data_base_path = os.path.join(self.ctx.env_base_dir, ".sage_states", "refiner_data")
            else:
                # 使用默认路径
                self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "refiner_data")

            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _save_data_record(self, question, input_docs, refined_docs):
        """保存精炼数据记录"""
        if not self.enable_profile:
            return

        record = {
            'timestamp': time.time(),
            'question': question,
            'input_docs': input_docs,
            'refined_docs': refined_docs,
            'budget': self.cfg["budget"]
        }
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        """将数据记录持久化到文件"""
        if not self.enable_profile or not self.data_records:
            return

        timestamp = int(time.time())
        filename = f"refiner_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def _init_refiner(self):
        if self.refiner is None:
            self.refiner = LongRefiner(
                base_model_path=self.cfg["base_model_path"],
                query_analysis_module_lora_path=self.cfg["query_analysis_module_lora_path"],
                doc_structuring_module_lora_path=self.cfg["doc_structuring_module_lora_path"],
                global_selection_module_lora_path=self.cfg["global_selection_module_lora_path"],
                score_model_name=self.cfg["score_model_name"],
                score_model_path=self.cfg["score_model_path"],
                max_model_len=self.cfg["max_model_len"],
            )

    def execute(self, data):
        question, docs = data  # SAGE 通常传入 (query, docs_list)
        self._init_refiner()

        # 按 LongRefiner 要求，把 docs 转为 [{"contents": str}, ...]
        texts = []
        if isinstance(docs, list):
            for d in docs:
                if isinstance(d, dict) and "text" in d:
                    texts.append(d["text"])
                elif isinstance(d, str):
                    texts.append(d)
        document_list = [{"contents": t} for t in texts]

        # 运行压缩
        try:
            refined_items = self.refiner.run(question, document_list, budget=self.cfg["budget"])
        except Exception:
            # 避免索引越界或模型加载失败
            return question, []

        # 最终把每个 item["contents"] 拿出来
        refined_texts = [item["contents"] for item in refined_items]

        # 保存数据记录（只有enable_profile=True时才保存）
        if self.enable_profile:
            self._save_data_record(question, texts, refined_texts)

        return question, refined_texts

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, 'enable_profile') and self.enable_profile:
            try:
                self._persist_data_records()
            except:
                pass
