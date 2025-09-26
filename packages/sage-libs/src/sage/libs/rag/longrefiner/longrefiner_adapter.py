import json
import os
import time

from sage.common.config.output_paths import get_states_file
from sage.core.api.function.map_function import MapFunction
from sage.libs.rag.longrefiner.longrefiner.refiner import LongRefiner


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

        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            # Use unified output path system
            self.data_base_path = str(get_states_file("dummy", "refiner_data").parent)
            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

        self._init_refiner()

    def _save_data_record(self, question, input_docs, refined_docs):
        """保存精炼数据记录"""
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "question": question,
            "input_docs": input_docs,
            "refined_docs": refined_docs,
            "budget": self.cfg["budget"],
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
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def _init_refiner(self):
        # 从配置中获取 GPU 设备参数，默认为 0
        gpu_device = self.cfg.get("gpu_device", 0)
        # score_gpu_device 如果不存在则使用与 gpu_device 相同的值
        score_gpu_device = self.cfg.get("score_gpu_device", gpu_device)
        gpu_memory_utilization = self.cfg.get(
            "gpu_memory_utilization", 0.7
        )  # GPU内存占比，默认为0.7

        self.logger.info(
            f"正在初始化LongRefiner，主模型使用GPU {gpu_device}，Score模型使用GPU {score_gpu_device}，GPU内存占比: {gpu_memory_utilization}"
        )

        self.refiner = LongRefiner(
            base_model_path=self.cfg["base_model_path"],
            query_analysis_module_lora_path=self.cfg["query_analysis_module_lora_path"],
            doc_structuring_module_lora_path=self.cfg[
                "doc_structuring_module_lora_path"
            ],
            global_selection_module_lora_path=self.cfg[
                "global_selection_module_lora_path"
            ],
            score_model_name=self.cfg["score_model_name"],
            score_model_path=self.cfg["score_model_path"],
            max_model_len=self.cfg["max_model_len"],
            gpu_device=gpu_device,
            gpu_memory_utilization=gpu_memory_utilization,
            score_gpu_device=score_gpu_device,  # 使用配置文件中的score_gpu_device
        )

        self.logger.info(
            f"LongRefiner初始化成功，主模型使用GPU {gpu_device}，Score模型使用GPU {score_gpu_device}"
        )

    def execute(self, data):
        # 处理不同的输入格式
        if isinstance(data, dict):
            # 获取查询
            question = data.get("query", "")

            # 优先从results字段获取文档，如果为空则从references字段获取
            docs = data.get("results", [])
            if not docs:
                docs = data.get("references", [])

        elif isinstance(data, tuple) and len(data) == 2:
            # 元组格式: (query, docs_list)
            question, docs = data
        else:
            # 其他格式，尝试转换
            self.logger.error(
                f"Unexpected input format for LongRefinerAdapter: {type(data)}"
            )
            if hasattr(data, "get"):
                question = data.get("query", str(data))
                docs = data.get("results", [])
                if not docs:
                    docs = data.get("references", [])
            else:
                question = str(data)
                docs = []

        # 按 LongRefiner 要求，把 docs 转为 [{"contents": str}, ...]
        texts = []
        if isinstance(docs, list):
            for d in docs:
                if isinstance(d, dict) and "text" in d:
                    # 标准格式: {"text": "..."}（来自Wiki18FAISSRetriever）
                    doc_text = d["text"]

                    # 如果文档有标题，添加标题格式以提高LongRefiner的解析成功率
                    if "title" in d and d["title"]:
                        # 模仿test_real_data.py中成功的格式：标题\n标题 内容...
                        formatted_text = f"{d['title']}\n{d['title']} {doc_text}"
                    else:
                        # 没有标题的话，尝试从内容开头提取标题
                        lines = doc_text.split("\n")
                        if lines and len(lines[0]) < 100:  # 第一行可能是标题
                            first_line = lines[0].strip()
                            if first_line:
                                formatted_text = f"{first_line}\n{doc_text}"
                            else:
                                formatted_text = doc_text
                        else:
                            formatted_text = doc_text

                    texts.append(formatted_text)
                elif isinstance(d, str):
                    # 直接的字符串格式（来自references字段）
                    texts.append(d)
                else:
                    # 其他情况，尝试将字典转为字符串
                    self.logger.warning(
                        f"Unknown document format: {type(d)}, keys: {d.keys() if isinstance(d, dict) else 'N/A'}"
                    )
                    texts.append(str(d))
        document_list = [{"contents": t} for t in texts]

        # 运行压缩
        try:
            refine_start_time = time.time()  # 记录开始时间
            refined_items = self.refiner.run(
                question, document_list, budget=self.cfg["budget"]
            )
            refine_end_time = time.time()  # 记录结束时间
            refine_time = refine_end_time - refine_start_time

            # 检查返回结果是否为空
            if not refined_items:
                self.logger.warning("LongRefiner returned empty results")
                refined_texts = []
            elif isinstance(refined_items, list) and len(refined_items) > 0:
                # LongRefiner.run() 实际返回 List[str] 格式（多个文档片段）
                if all(isinstance(item, str) for item in refined_items):
                    # 所有项都是字符串，直接使用
                    refined_texts = refined_items
                else:
                    # 有其他类型，尝试转换为字符串
                    self.logger.warning(
                        f"LongRefiner returned mixed types: {[type(item) for item in refined_items[:3]]}"
                    )
                    refined_texts = [str(item) for item in refined_items]
            else:
                self.logger.warning(
                    f"LongRefiner returned unexpected format: {type(refined_items)}"
                )
                refined_texts = []

        except Exception as e:
            # 避免索引越界或模型加载失败
            self.logger.error(f"LongRefiner execution failed: {str(e)}")
            refined_texts = []
            refine_time = 0.0  # 失败时设置时间为0

        # 保存数据记录（只有enable_profile=True时才保存）
        if self.enable_profile:
            self._save_data_record(question, texts, refined_texts)

        # 返回字典格式，保持所有原始字段
        result = data.copy()  # 保持原始数据的所有字段
        result["results"] = [
            {"text": text} for text in refined_texts
        ]  # 统一使用results字段，与检索器输出格式保持一致
        result["refined_docs"] = refined_texts  # 添加精炼后的文档列表
        result["refine_time"] = refine_time  # 添加精炼时间
        return result

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except:
                pass
