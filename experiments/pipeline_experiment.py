import logging
import json
import time
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv
from sage.common.utils.config.loader import load_config
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.local_environment import LocalEnvironment
from sage.common.config.output_paths import get_output_file


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


class BatchFileSource(BatchFunction):
    """批量文件数据源算子，读取测试数据并支持批量处理"""

    def __init__(self, config: dict):
        self.config = config
        self.data_path = config.get("data_path")
        self.max_samples = config.get("max_samples", None)
        data = self.load_test_data()
        if self.max_samples:
            data = data[: self.max_samples]
        # 先加载数据以确定默认批次大小
        self.batch_size = config.get("batch_size", len(data))  # 默认为整个数据集大小
        self.current_batch = 0  # 当前批次索引
        self.total_batches = (len(data) + self.batch_size - 1) // self.batch_size

    def load_test_data(self) -> List[Dict[str, Any]]:
        """加载测试数据"""
        data = []
        with open(self.data_path, "r", encoding="utf-8") as f:
            for line in f:
                data.append(json.loads(line))
        return data

    def execute(self):
        """处理数据源，返回所有批次的数据"""
        data = self.load_test_data()

        # 如果已经处理完所有批次，返回 None 表示没有更多数据
        if self.current_batch >= self.total_batches:
            return None

        # 获取当前批次的数据
        start_idx = self.current_batch * self.batch_size
        end_idx = min(start_idx + self.batch_size, len(data))
        batch = data[start_idx:end_idx]

        result = {
            "batch_data": batch,
            "batch_id": self.current_batch,
            "total_batches": self.total_batches,
        }

        # 更新当前批次索引
        self.current_batch += 1

        return result


class Generator(MapFunction):
    """实验生成算子，生成模型回答"""

    def __init__(self, config: dict):
        self.config = config
        self.model_name = config.get("model_name", "Mistral-7B-Instruct-v0.1")
        self.use_context = config.get("use_context", True)  # 控制是否使用检索上下文
        self.top_k = config.get("top_k", 3)

        from vllm import LLM, SamplingParams

        self.llm = LLM(model=self.model_name, gpu_memory_utilization=0.8)
        self.sampling_params = SamplingParams(temperature=0, max_tokens=100)

    def get_retrieved_docs_from_data(self, item: Dict[str, Any]) -> List[str]:
        """从数据中提取已检索的文档"""
        retrieved_docs = []
        ctxs = item.get("ctxs", [])

        for ctx in ctxs[: self.top_k]:
            if "text" in ctx and ctx["text"].strip():
                retrieved_docs.append(ctx["text"])

        return retrieved_docs

    def build_prompt(self, question: str, context: str = None) -> str:
        """构建提示词"""
        if self.use_context and context:
            if "llama" in self.model_name.lower():
                prompt = f"[INST]{context}\n{question}[/INST]"
            else:
                prompt = f"<s>[INST]{context}\n{question}[/INST]"
        else:
            if "llama" in self.model_name.lower():
                prompt = f"[INST]{question}[/INST]"
            else:
                prompt = f"### Instruction:\n{question}\n\n### Response:\n"

        return prompt

    def execute(self, batch_data: dict):
        """处理一个批次的数据"""
        batch = batch_data["batch_data"]
        prompts = []
        batch_with_context = []  # 保存带有上下文信息的批次数据

        # 为批次中的每个问题构建提示词
        for item in batch:
            question = item["question"]
            context = None
            retrieved_context = []

            if self.use_context:
                # 使用数据中已有的检索文档
                retrieved_docs = self.get_retrieved_docs_from_data(item)
                if retrieved_docs:
                    # 构建evidence paragraph
                    evidences = []
                    ctxs = item.get("ctxs", [])[: self.top_k]
                    for i, ctx in enumerate(ctxs):
                        if "text" in ctx and ctx["text"].strip():
                            title = ctx.get("title", "")
                            evidence = f"[{i+1}] {title}\n{ctx['text']}"
                            evidences.append(evidence)
                            retrieved_context.append(ctx["text"])  # 保存原始上下文文本
                    context = "\n".join(evidences)

            prompt = self.build_prompt(question, context)
            prompts.append(prompt)

            # 创建带有上下文信息的item副本
            item_with_context = item.copy()
            if retrieved_context:
                item_with_context["retrieved_context"] = retrieved_context
            batch_with_context.append(item_with_context)

        # 使用VLLM
        outputs = self.llm.generate(prompts, self.sampling_params)
        responses = [output.outputs[0].text for output in outputs]

        # 返回带有原始数据、上下文信息和生成回答的结果
        return {
            "batch_data": batch_with_context,  # 使用带有上下文信息的数据
            "responses": responses,
            "batch_id": batch_data["batch_id"],
            "total_batches": batch_data["total_batches"],
        }


class PostProcessor(MapFunction):
    """后处理算子，处理答案并进行预测"""

    def __init__(self, config: dict):
        self.config = config
        self.extract_prediction = config.get("extract_prediction", True)

    def postprocess_model_output(self, generated_text: str) -> str:
        """统一的模型输出后处理函数"""
        # 取第一段内容（遇到双换行符停止）
        processed_text = generated_text.split("\n\n")[0]

        # 移除结束标记
        processed_text = processed_text.replace("</s>", "")

        # 移除开头的空格
        if len(processed_text) > 0 and processed_text[0] == " ":
            processed_text = processed_text[1:]

        return processed_text

    def execute(self, batch_result: dict):
        """处理批次结果"""
        batch_data = batch_result["batch_data"]
        responses = batch_result["responses"]

        processed_results = []

        for i, (item, response) in enumerate(zip(batch_data, responses)):
            # 后处理回答
            processed_response = self.postprocess_model_output(response)

            # 按照指定格式创建结果项
            result_item = {
                "id": item.get("id", i),
                "question": item["question"],
                "ground_truth": item.get("answers", []),
                "model_output": processed_response,
            }

            # 如果在Generator中已经保存了检索上下文，直接使用
            if "retrieved_context" in item:
                result_item["retrieved_context"] = item["retrieved_context"]

            processed_results.append(result_item)

        return {
            "results": processed_results,
            "batch_id": batch_result["batch_id"],
            "total_batches": batch_result["total_batches"],
        }


class Sink(MapFunction):
    """实验结果保存算子"""

    def __init__(self, config: dict):
        self.config = config
        default_output_path = get_output_file("experiment_results.json", "experiments")
        self.output_path = config.get("output_path", str(default_output_path))
        self.save_mode = config.get(
            "save_mode", "incremental"
        )  # 'incremental' 或 'final'
        self.all_results = []

    def execute(self, processed_batch: dict):
        """处理并保存实验结果"""
        batch_results = processed_batch["results"]
        batch_id = processed_batch["batch_id"]
        total_batches = processed_batch["total_batches"]

        # 添加到总结果中
        self.all_results.extend(batch_results)

        logging.info(
            f"✅ 已处理批次 {batch_id + 1}/{total_batches}，当前总结果数: {len(self.all_results)}"
        )

        # 根据保存模式决定何时保存
        if self.save_mode == "incremental":
            self._save_results(batch_id + 1, total_batches)
        elif self.save_mode == "final" and batch_id + 1 == total_batches:
            self._save_results(batch_id + 1, total_batches)

    def _save_results(self, current_batch: int, total_batches: int):
        """保存结果到文件"""
        from datetime import datetime

        results = {
            "experiment_config": {
                "model_name": self.config.get("model_name", "unknown"),
                "use_context": self.config.get("use_context", True),
                "top_k": self.config.get("top_k", 5),
                "batch_size": self.config.get("batch_size", 10),
                "timestamp": datetime.now().isoformat(),
                "total_samples": len(self.all_results),
                "completed_batches": f"{current_batch}/{total_batches}",
            },
            "results": self.all_results,
        }

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logging.info(f"📁 结果已保存到: {self.output_path}")


def pipeline_run(config: dict) -> None:
    """
    创建并运行实验数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """
    env = LocalEnvironment()

    # 构建数据处理流程
    (
        env.from_source(BatchFileSource, config["source"])
        .map(Generator, config["generator"])
        .map(PostProcessor, config["post_processor"])
        .sink(Sink, config["sink"])
    )

    env.submit()
    # env.run()
    # time.sleep(10)  # 等待管道运行5秒
    env.close()

    # # 创建算子实例
    # source = BatchFileSource(config["source"])
    # generator = Generator(config["generator"])
    # post_processor = PostProcessor(config["post_processor"])
    # sink = Sink(config["sink"])

    # # 处理每个批次
    # for batch_data in source.execute():
    #     batch_result = generator.execute(batch_data)
    #     processed_batch = post_processor.execute(batch_result)
    #     sink.execute(processed_batch)


if __name__ == "__main__":
    from sage.common.utils.logging.custom_logger import CustomLogger

    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    # 加载配置文件
    config_path = "./experiments/config/experiment_config.yaml"
    config = load_config(config_path)

    logging.info("🚀 开始运行实验管道...")
    logging.info(f"📊 数据文件: {config['source']['data_path']}")
    logging.info(f"🔄 使用上下文: {config['generator']['use_context']}")
    logging.info(f"💾 输出路径: {config['sink']['output_path']}")

    pipeline_run(config)
