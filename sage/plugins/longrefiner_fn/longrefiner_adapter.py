from sage.core.function.map_function import MapFunction

from sage_plugins.longrefiner_fn.longrefiner.refiner import LongRefiner

class LongRefinerAdapter(MapFunction):
    def __init__(self, config: dict, ctx=None):
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
        # 只在第一次 execute 时初始化
        self.refiner: LongRefiner | None = None

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

        # 最终把每个 item["contents"] 拿出来，返回 (query, [str,…])
        refined_texts = [item["contents"] for item in refined_items]
        return question, refined_texts