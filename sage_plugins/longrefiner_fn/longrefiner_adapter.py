from sage_core.function.map_function import MapFunction
from sage_plugins.longrefiner_fn.longrefiner.refiner import LongRefiner

class LongRefinerAdapter(MapFunction):
    def __init__(self, config: dict, ctx):
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
            raise RuntimeError(f"LongRefinerAdapter 缺少配置字段: {missing}")
        self.cfg = config
        # 直接用 vendor 版 LongRefiner
        self.refiner = LongRefiner(
            base_model_path=config["base_model_path"],
            query_analysis_module_lora_path=config["query_analysis_module_lora_path"],
            doc_structuring_module_lora_path=config["doc_structuring_module_lora_path"],
            global_selection_module_lora_path=config["global_selection_module_lora_path"],
            score_model_name=config["score_model_name"],
            score_model_path=config["score_model_path"],
            max_model_len=config["max_model_len"],
        )

    def execute(self, data):
        question, docs = data
        # 文本提取
        if docs and isinstance(docs[0], dict) and "text" in docs[0]:
            texts = [d["text"] for d in docs]
        else:
            texts = docs or []
        if not texts:
            return (question, "")
        # 一层包装
        document_list = [{"contents": txt} for txt in texts]
        # 调用原封不动的 LongRefiner.run
        try:
            refined = self.refiner.run(question, document_list, budget=self.cfg["budget"])
        except IndexError:
            return (question, "")
        if not refined:
            return (question, "")
        # 拼接
        context = "\n".join(item["contents"] for item in refined)
        return (question, context)