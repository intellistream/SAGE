import re
import string
from collections import Counter

from rouge import Rouge
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer

from sage.common.core.functions import MapFunction as MapOperator
from sage.kernel.runtime.communication.packet import StopSignal

# =============================================================================
# RECOMP-style Answer Normalization (标准化答案文本)
# =============================================================================


def normalize_answer(s: str) -> str:
    """RECOMP 风格的答案标准化

    步骤:
    1. 转小写
    2. 移除标点符号
    3. 移除冠词 (a, an, the)
    4. 修复空白字符

    Args:
        s: 原始答案文本

    Returns:
        标准化后的答案文本
    """

    def remove_articles(text: str) -> str:
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text: str) -> str:
        return " ".join(text.split())

    def remove_punc(text: str) -> str:
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text: str) -> str:
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def get_normalized_tokens(s: str) -> list[str]:
    """获取标准化后的 token 列表

    Args:
        s: 原始文本

    Returns:
        标准化后的 token 列表
    """
    if not s:
        return []
    return normalize_answer(s).split()


def answer_extract(pred: str) -> str:
    """提取答案文本

    支持 "answer is" 前缀格式的答案提取。

    Args:
        pred: 预测文本

    Returns:
        提取后的答案文本
    """
    prefix = "answer is "
    if prefix in pred.lower():
        idx = pred.lower().rfind(prefix)
        return pred[idx + len(prefix) :].strip()
    return pred.strip()


def _get_results_collector():
    """
    延迟导入 ResultsCollector 以避免循环依赖

    Returns:
        ResultsCollector 实例，如果不可用则返回 None
    """
    try:
        from sage.common.utils.results_collector import ResultsCollector

        return ResultsCollector()
    except ImportError:
        return None


class MetricsAggregator:
    """全局指标聚合器，用于收集和计算平均指标"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.reset()
        return cls._instance

    def reset(self):
        """重置所有统计数据"""
        self.metrics = {
            "f1_scores": [],
            "em_scores": [],  # Exact Match scores
            "token_counts": [],
            "retrieve_times": [],
            "refine_times": [],
            "generate_times": [],
            "total_latencies": [],
            "compression_rates": [],
        }
        self.sample_count = 0

    def add_f1(self, score):
        self.metrics["f1_scores"].append(score)

    def add_em(self, score):
        """添加 Exact Match 分数"""
        self.metrics["em_scores"].append(score)

    def add_token_count(self, count):
        self.metrics["token_counts"].append(count)

    def add_latency(self, retrieve, refine, generate):
        self.metrics["retrieve_times"].append(retrieve)
        self.metrics["refine_times"].append(refine)
        self.metrics["generate_times"].append(generate)
        self.metrics["total_latencies"].append(retrieve + refine + generate)
        self.sample_count += 1

    def add_compression_rate(self, rate):
        self.metrics["compression_rates"].append(rate)

    def print_summary(self):
        """打印汇总统计信息"""
        if self.sample_count == 0:
            print("\n" + "=" * 80)
            print("No samples processed")
            print("=" * 80)
            return

        print("\n" + "=" * 80)
        print(f"SUMMARY STATISTICS ({self.sample_count} samples)")
        print("=" * 80)

        # Exact Match Score
        if self.metrics["em_scores"]:
            avg_em = sum(self.metrics["em_scores"]) / len(self.metrics["em_scores"])
            print(f"\033[92m[Average EM Score]        : {avg_em:.4f}\033[0m")

        # F1 Score
        if self.metrics["f1_scores"]:
            avg_f1 = sum(self.metrics["f1_scores"]) / len(self.metrics["f1_scores"])
            print(f"\033[92m[Average F1 Score]        : {avg_f1:.4f}\033[0m")

        # Token Count
        if self.metrics["token_counts"]:
            avg_tokens = sum(self.metrics["token_counts"]) / len(self.metrics["token_counts"])
            print(f"\033[92m[Average Token Count]     : {avg_tokens:.0f}\033[0m")

        # Latency
        if self.metrics["retrieve_times"]:
            avg_retrieve = sum(self.metrics["retrieve_times"]) / len(self.metrics["retrieve_times"])
            avg_refine = sum(self.metrics["refine_times"]) / len(self.metrics["refine_times"])
            avg_generate = sum(self.metrics["generate_times"]) / len(self.metrics["generate_times"])
            avg_total = sum(self.metrics["total_latencies"]) / len(self.metrics["total_latencies"])

            print(f"\033[92m[Average Retrieve Time]   : {avg_retrieve:.2f}s\033[0m")
            print(f"\033[92m[Average Refine Time]     : {avg_refine:.2f}s\033[0m")
            print(f"\033[92m[Average Generate Time]   : {avg_generate:.2f}s\033[0m")
            avg_min = avg_total / 60
            print(f"\033[92m[Average Total Latency]   : {avg_total:.2f}s ({avg_min:.2f}m)\033[0m")

        # Compression Rate
        if self.metrics["compression_rates"]:
            valid_rates = [r for r in self.metrics["compression_rates"] if r > 0]
            if valid_rates:
                avg_compression = sum(valid_rates) / len(valid_rates)
                print(f"\033[92m[Average Compression Rate]: {avg_compression:.2f}×\033[0m")

        print("=" * 80 + "\n")


class F1Evaluate(MapOperator):
    """F1分数评估器（RECOMP 标准）

    使用 RECOMP 风格的答案标准化进行 F1 分数计算。
    标准化步骤：转小写、移除标点、移除冠词、修复空白。

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.aggregator = MetricsAggregator()
        # 是否提取 "answer is" 前缀后的答案
        self.extract_answer = config.get("extract_answer", False) if config else False

    def _f1_score(self, pred: str, ref: str) -> float:
        """计算 F1 分数（RECOMP 标准）

        使用标准化后的 token 进行计算。

        Args:
            pred: 预测答案
            ref: 参考答案

        Returns:
            F1 分数
        """
        gold_toks = get_normalized_tokens(ref)
        pred_toks = get_normalized_tokens(pred)

        common = Counter(gold_toks) & Counter(pred_toks)
        num_same = sum(common.values())

        if len(gold_toks) == 0 or len(pred_toks) == 0:
            # If either is no-answer, then F1 is 1 if they agree, 0 otherwise
            return float(gold_toks == pred_toks)

        if num_same == 0:
            return 0.0

        precision = 1.0 * num_same / len(pred_toks)
        recall = 1.0 * num_same / len(gold_toks)
        f1 = (2 * precision * recall) / (precision + recall)
        return f1

    def execute(self, data):
        # Handle StopSignal - 不输出,让 CompressionRateEvaluate 最后统一输出
        if isinstance(data, StopSignal):
            return data

        golds = data.get("references", [])
        pred = data.get("generated", "")

        # 可选：提取 "answer is" 后的答案
        if self.extract_answer:
            pred = answer_extract(pred)

        best = max((self._f1_score(pred, g) for g in golds), default=0.0) if golds else 0.0

        # Add to aggregator
        self.aggregator.add_f1(best)

        # Add to ResultsCollector (if available)
        collector = _get_results_collector()
        if collector is not None:
            sample_id = data.get("sample_id", data.get("_sample_idx"))
            collector.update_sample(sample_id, f1=best)

        print(f"\033[93m[F1] : {best:.4f}\033[0m")
        return data


class EMEvaluate(MapOperator):
    """Exact Match 评估器（RECOMP 标准）

    使用 RECOMP 风格的答案标准化进行精确匹配计算。
    标准化步骤：转小写、移除标点、移除冠词、修复空白。

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.aggregator = MetricsAggregator()
        # 是否提取 "answer is" 前缀后的答案
        self.extract_answer = config.get("extract_answer", False) if config else False

    def _exact_match(self, pred: str, gold: str) -> int:
        """计算 Exact Match（RECOMP 标准）

        使用标准化后的文本进行精确匹配。

        Args:
            pred: 预测答案
            gold: 参考答案

        Returns:
            1 如果匹配，否则 0
        """
        return int(normalize_answer(pred) == normalize_answer(gold))

    def execute(self, data):
        # Handle StopSignal - 不输出,让 CompressionRateEvaluate 最后统一输出
        if isinstance(data, StopSignal):
            return data

        golds = data.get("references", [])
        pred = data.get("generated", "")

        # 可选：提取 "answer is" 后的答案
        if self.extract_answer:
            pred = answer_extract(pred)

        best = max((self._exact_match(pred, g) for g in golds), default=0) if golds else 0

        # Add to aggregator
        self.aggregator.add_em(best)

        print(f"\033[93m[EM] : {best}\033[0m")
        return data


class RecallEvaluate(MapOperator):
    """Recall评估器

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

    def _get_tokens(self, text: str):
        return text.lower().split()

    def _recall(self, pred: str, ref: str):
        r = Counter(self._get_tokens(ref))
        p = Counter(self._get_tokens(pred))
        if not r:
            return 0.0
        common = r & p
        return float(sum(common.values()) / sum(r.values()))

    def execute(self, data: dict):
        golds = data.get("references", [])
        pred = data.get("generated", "")
        best = max(self._recall(pred, g) for g in golds) if golds else 0.0
        print(f"\033[93m[Recall] : {best:.4f}\033[0m")
        return data


class BertRecallEvaluate(MapOperator):
    """BERT Recall评估器

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.model = AutoModel.from_pretrained("bert-base-uncased")

    def execute(self, data: dict):
        golds = data.get("references", [])
        pred = data.get("generated", "")
        scores = []
        for g in golds:
            encs = self.tokenizer([pred, g], return_tensors="pt", padding=True)
            embs = self.model(**encs).last_hidden_state.mean(dim=1).detach().numpy()
            # Convert to numpy arrays explicitly for cosine_similarity
            emb_pred = embs[0:1]  # Shape: (1, embedding_dim)
            emb_gold = embs[1:2]  # Shape: (1, embedding_dim)
            similarity = cosine_similarity(emb_pred, emb_gold)
            scores.append(float(similarity[0][0]))
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BertRecall] : {best:.4f}\033[0m")
        return data


class RougeLEvaluate(MapOperator):
    """ROUGE-L评估器

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.rouge = Rouge()

    def execute(self, data: dict):
        golds = data.get("references", [])
        pred = data.get("generated", "")
        scores = []
        for g in golds:
            # rouge.get_scores returns a list with one dict
            rouge_result = self.rouge.get_scores(pred, g)
            if rouge_result and isinstance(rouge_result, list):
                scores.append(rouge_result[0]["rouge-l"]["f"])
        best = max(scores) if scores else 0.0
        print(f"\033[93m[ROUGE-L] : {best:.4f}\033[0m")
        return data


class BRSEvaluate(MapOperator):
    """BRS评估器

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

    def execute(self, data: dict):
        golds = data.get("references", [])
        pred = data.get("generated", "")
        scores = [(len(set(pred) & set(g)) / len(set(g))) if g else 0.0 for g in golds]
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BRS] : {best:.4f}\033[0m")
        return data


class AccuracyEvaluate(MapOperator):
    """准确率评估器

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

    def _normalize_text(self, text: str) -> str:
        """标准化文本用于比较"""
        return text.lower().strip()

    def execute(self, data: dict):
        golds = data.get("references", [])
        pred = data.get("generated", "")

        if not golds or not pred:
            print("\033[93m[Acc] : 0.0000\033[0m")
            return data

        pred_norm = self._normalize_text(pred)

        # 准确率：检查预测答案是否与任一参考答案匹配（完全匹配或关键词匹配）
        correct = False
        for gold in golds:
            gold_norm = self._normalize_text(gold)
            # 检查是否有关键词匹配
            gold_words = set(gold_norm.split())
            pred_words = set(pred_norm.split())
            # 如果预测答案包含参考答案中的重要词汇，认为是正确的
            if gold_words and len(gold_words & pred_words) / len(gold_words) >= 0.3:
                correct = True
                break

        print(f"\033[93m[Acc] : {float(correct):.4f}\033[0m")
        return data


class TokenCountEvaluate(MapOperator):
    """Token计数评估器

    统计送入生成器的最终prompt的token数量（使用真实tokenizer）
    优先级：compressed_context（压缩后）> refining_results > retrieval_results（原始）

    输入数据格式：{"query": str, "compressed_context": str, "refining_results": List[str], ...} 或
                 {"query": str, "retrieval_results": List[Dict], ...}
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.aggregator = MetricsAggregator()
        # 使用与REFORM相同的tokenizer以保持一致性
        try:
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
        except Exception:
            self.tokenizer = None

    def execute(self, data):
        # Handle StopSignal
        if isinstance(data, StopSignal):
            return data

        # 优先使用 compressed_context（最终送入生成器的文本）
        context = data.get("compressed_context")
        if context:
            # 使用真实tokenizer计算token数
            if self.tokenizer:
                total_tokens = len(self.tokenizer.encode(context))
            else:
                total_tokens = len(context.split())
        else:
            # 回退到旧的计算方式
            docs = data.get("refining_results") or data.get("retrieval_results", [])
            total_tokens = 0
            if docs:
                for doc in docs:
                    if isinstance(doc, dict):
                        text = doc.get("text", str(doc))
                    elif isinstance(doc, str):
                        text = doc
                    else:
                        text = str(doc)

                    if self.tokenizer:
                        total_tokens += len(self.tokenizer.encode(text))
                    else:
                        total_tokens += len(text.split())

        # Add to aggregator
        self.aggregator.add_token_count(total_tokens)

        # Add to ResultsCollector (if available)
        collector = _get_results_collector()
        if collector is not None:
            sample_id = data.get("sample_id", data.get("_sample_idx"))
            collector.update_sample(sample_id, token_count=total_tokens)

        print(f"\033[93m[Token Count] : {total_tokens}\033[0m")
        return data


class LatencyEvaluate(MapOperator):
    """延迟评估器

    输入数据格式:
        {"query": str, "retrieve_time": float, "refine_time": float,
         "generate_time": float, ...}
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.aggregator = MetricsAggregator()

    def execute(self, data):
        # Handle StopSignal - 不输出,让 CompressionRateEvaluate 最后统一输出
        if isinstance(data, StopSignal):
            return data

        retrieve_time = data.get("retrieve_time", 0)
        refine_time = data.get("refine_time", 0.0)
        generate_time = data.get("generate_time", 0.0)
        total_lat = retrieve_time + refine_time + generate_time

        # Add to aggregator
        self.aggregator.add_latency(retrieve_time, refine_time, generate_time)

        # Add to ResultsCollector (if available)
        collector = _get_results_collector()
        if collector is not None:
            sample_id = data.get("sample_id", data.get("_sample_idx"))
            collector.update_sample(
                sample_id,
                retrieve_time=retrieve_time,
                refine_time=refine_time,
                generate_time=generate_time,
                total_time=total_lat,
            )

        print(f"\033[93m[Retrieve Time] : {retrieve_time:.2f}s\033[0m")
        print(f"\033[93m[Refine Time]   : {refine_time:.2f}s\033[0m")
        print(f"\033[93m[Generate Time] : {generate_time:.2f}s\033[0m")
        print(f"\033[93m[Total Latency] : {total_lat:.2f}s\033[0m")
        return data


class ContextRecallEvaluate(MapOperator):
    """上下文召回率评估器

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

    def _normalize_text(self, text: str) -> str:
        """标准化文本用于比较"""
        return text.lower().strip()

    def execute(self, data: dict):
        golds = data.get("references", [])
        pred = data.get("generated", "")

        if not golds or not pred:
            print("\033[93m[Context Recall] : 0.0000\033[0m")
            return data

        pred_norm = self._normalize_text(pred)
        pred_words = set(pred_norm.split())

        # 计算有多少参考答案的关键词在生成答案中被提及
        total_recall = 0.0
        for gold in golds:
            gold_norm = self._normalize_text(gold)
            gold_words = set(gold_norm.split())
            if gold_words:
                # 计算当前参考答案的recall
                matched_words = len(gold_words & pred_words)
                recall = matched_words / len(gold_words)
                total_recall = max(total_recall, recall)  # 取最大值

        print(f"\033[93m[Context Recall] : {total_recall:.4f}\033[0m")
        return data


class CompressionRateEvaluate(MapOperator):
    """计算文档压缩率

    压缩率 = 原始文档token数 / 压缩后文档token数

    输入数据格式:
        {"query": str, "retrieval_results": List[Dict],
         "refining_results": List[str], ...}

    Args:
        retrieval_results: 原始检索的文档（用于计算原始token数）
        refining_results: 压缩后的文档文本（用于计算压缩后token数）
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.aggregator = MetricsAggregator()

    def _count_tokens(self, docs):
        """计算文档列表的总token数"""
        if not docs:
            return 0
        # 处理不同格式的文档
        total = 0
        for doc in docs:
            if isinstance(doc, dict):
                # Dict格式：提取text字段
                text = doc.get("text", doc.get("content", str(doc)))
                total += len(text.split())
            elif isinstance(doc, str):
                # 字符串格式
                total += len(doc.split())
            else:
                total += len(str(doc).split())
        return total

    def execute(self, data):
        # Handle StopSignal - 在最后输出完整汇总统计
        if isinstance(data, StopSignal):
            print("\n")  # 添加空行分隔
            self.aggregator.print_summary()
            return data

        # 获取原始检索文档的token数
        retrieved_docs = data.get("retrieval_results", [])
        retrieved_tokens = self._count_tokens(retrieved_docs)

        # 获取压缩后文档的token数
        refined_docs = data.get("refining_results", [])
        refined_tokens = self._count_tokens(refined_docs)

        # 计算压缩率
        if refined_tokens > 0 and retrieved_tokens > 0:
            compression_rate = retrieved_tokens / refined_tokens
        else:
            compression_rate = 0.0

        # Add to aggregator
        self.aggregator.add_compression_rate(compression_rate)

        # Add to ResultsCollector (if available)
        collector = _get_results_collector()
        if collector is not None:
            sample_id = data.get("sample_id", data.get("_sample_idx"))
            collector.update_sample(
                sample_id,
                compression_rate=compression_rate,
                original_tokens=retrieved_tokens,
                compressed_tokens=refined_tokens,
            )

        print(f"\033[93m[Compression Rate] : {compression_rate:.2f}×\033[0m")
        return data


# ============================================================================
# LongBench Evaluator - 用于 LongBench 基准测试
# ============================================================================

# 数据集到评估指标的映射（来自 LongBench/eval.py）
LONGBENCH_DATASET_TO_METRIC: dict[str, str] = {
    # QA 任务 - F1 score
    "narrativeqa": "qa_f1",
    "qasper": "qa_f1",
    "multifieldqa_en": "qa_f1",
    "hotpotqa": "qa_f1",
    "2wikimqa": "qa_f1",
    "musique": "qa_f1",
    "triviaqa": "qa_f1",
    # 中文 QA（需要 jieba 分词）
    "multifieldqa_zh": "qa_f1_zh",
    # 摘要任务 - ROUGE score
    "gov_report": "rouge",
    "qmsum": "rouge",
    "multi_news": "rouge",
    "samsum": "rouge",
    # 中文摘要（需要 jieba 分词）
    "dureader": "rouge_zh",
    "vcsum": "rouge_zh",
    # 分类任务（需要 all_classes 参数）
    "trec": "classification",
    "lsht": "classification",
    # 检索任务
    "passage_retrieval_en": "retrieval",
    "passage_retrieval_zh": "retrieval_zh",
    "passage_count": "count",
    # 代码任务（需要 fuzzywuzzy）
    "lcc": "code_sim",
    "repobench-p": "code_sim",
}

# 需要取第一行的数据集
LONGBENCH_FIRST_LINE_DATASETS: set[str] = {"trec", "triviaqa", "samsum", "lsht"}


def _longbench_normalize_answer(s: str) -> str:
    """LongBench 英文答案标准化（与原始实现一致）"""

    def remove_articles(text: str) -> str:
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text: str) -> str:
        return " ".join(text.split())

    def remove_punc(text: str) -> str:
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text: str) -> str:
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def _longbench_normalize_zh_answer(s: str) -> str:
    """LongBench 中文答案标准化（与原始实现一致）"""

    def white_space_fix(text: str) -> str:
        return "".join(text.split())

    def remove_punc(text: str) -> str:
        cn_punctuation = (
            "！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—''‛"
            "„‟…‧﹏."
        )
        all_punctuation = set(string.punctuation + cn_punctuation)
        return "".join(ch for ch in text if ch not in all_punctuation)

    def lower(text: str) -> str:
        return text.lower()

    return white_space_fix(remove_punc(lower(s)))


def _longbench_f1_score(prediction_tokens: list, ground_truth_tokens: list) -> float:
    """LongBench F1 分数计算（token 级别）"""
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1


def longbench_qa_f1_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench QA F1 分数（英文）"""
    normalized_prediction = _longbench_normalize_answer(prediction)
    normalized_ground_truth = _longbench_normalize_answer(ground_truth)
    prediction_tokens = normalized_prediction.split()
    ground_truth_tokens = normalized_ground_truth.split()
    if not prediction_tokens or not ground_truth_tokens:
        return float(prediction_tokens == ground_truth_tokens)
    return _longbench_f1_score(prediction_tokens, ground_truth_tokens)


def longbench_qa_f1_zh_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench QA F1 分数（中文，需要 jieba）"""
    try:
        import jieba
    except ImportError:
        raise ImportError(
            "jieba is required for Chinese evaluation. Install with: pip install jieba"
        )

    prediction_tokens = list(jieba.cut(prediction, cut_all=False))
    ground_truth_tokens = list(jieba.cut(ground_truth, cut_all=False))
    prediction_tokens = [_longbench_normalize_zh_answer(token) for token in prediction_tokens]
    ground_truth_tokens = [_longbench_normalize_zh_answer(token) for token in ground_truth_tokens]
    prediction_tokens = [token for token in prediction_tokens if len(token) > 0]
    ground_truth_tokens = [token for token in ground_truth_tokens if len(token) > 0]
    if not prediction_tokens or not ground_truth_tokens:
        return float(prediction_tokens == ground_truth_tokens)
    return _longbench_f1_score(prediction_tokens, ground_truth_tokens)


def longbench_rouge_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench ROUGE-L F1 分数"""
    try:
        rouge = Rouge()
        scores = rouge.get_scores([prediction], [ground_truth], avg=True)
        return scores["rouge-l"]["f"]
    except Exception:
        return 0.0


def longbench_rouge_zh_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench ROUGE-L F1 分数（中文，需要 jieba）"""
    try:
        import jieba
    except ImportError:
        raise ImportError(
            "jieba is required for Chinese evaluation. Install with: pip install jieba"
        )

    prediction = " ".join(list(jieba.cut(prediction, cut_all=False)))
    ground_truth = " ".join(list(jieba.cut(ground_truth, cut_all=False)))
    return longbench_rouge_score(prediction, ground_truth)


def longbench_classification_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench 分类任务分数（需要 all_classes 参数）"""
    all_classes = kwargs.get("all_classes", [])
    if not all_classes:
        return 0.0

    em_match_list = []
    for class_name in all_classes:
        if class_name in prediction:
            em_match_list.append(class_name)

    # 移除部分匹配
    for match_term in em_match_list.copy():
        if match_term in ground_truth and match_term != ground_truth:
            em_match_list.remove(match_term)

    if ground_truth in em_match_list:
        score = 1.0 / len(em_match_list)
    else:
        score = 0.0
    return score


def longbench_retrieval_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench 检索任务分数（英文）"""
    pattern = r"Paragraph (\d+)"
    matches = re.findall(pattern, ground_truth)
    if not matches:
        return 0.0
    ground_truth_id = matches[0]
    numbers = re.findall(r"\d+", prediction)
    right_num = sum(1 for number in numbers if str(number) == str(ground_truth_id))
    return 0.0 if len(numbers) == 0 else float(right_num / len(numbers))


def longbench_retrieval_zh_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench 检索任务分数（中文）"""
    pattern = r"段落(\d+)"
    matches = re.findall(pattern, ground_truth)
    if not matches:
        return 0.0
    ground_truth_id = matches[0]
    numbers = re.findall(r"\d+", prediction)
    right_num = sum(1 for number in numbers if str(number) == str(ground_truth_id))
    return 0.0 if len(numbers) == 0 else float(right_num / len(numbers))


def longbench_count_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench 计数任务分数"""
    numbers = re.findall(r"\d+", prediction)
    right_num = sum(1 for number in numbers if str(number) == str(ground_truth))
    return 0.0 if len(numbers) == 0 else float(right_num / len(numbers))


def longbench_code_sim_score(prediction: str, ground_truth: str, **kwargs) -> float:
    """LongBench 代码相似度分数（需要 fuzzywuzzy）"""
    try:
        from fuzzywuzzy import fuzz
    except ImportError:
        raise ImportError(
            "fuzzywuzzy is required for code evaluation. "
            "Install with: pip install fuzzywuzzy python-Levenshtein"
        )

    # 代码后处理：取第一行有效代码（跳过注释和代码块标记）
    all_lines = prediction.lstrip("\n").split("\n")
    processed_prediction = ""
    for line in all_lines:
        if ("`" not in line) and ("#" not in line) and ("//" not in line):
            processed_prediction = line
            break

    return fuzz.ratio(processed_prediction, ground_truth) / 100.0


# 指标函数映射
LONGBENCH_METRIC_FUNCTIONS = {
    "qa_f1": longbench_qa_f1_score,
    "qa_f1_zh": longbench_qa_f1_zh_score,
    "rouge": longbench_rouge_score,
    "rouge_zh": longbench_rouge_zh_score,
    "classification": longbench_classification_score,
    "retrieval": longbench_retrieval_score,
    "retrieval_zh": longbench_retrieval_zh_score,
    "count": longbench_count_score,
    "code_sim": longbench_code_sim_score,
}


class LongBenchEvaluator(MapOperator):
    """
    LongBench 专用评估器。

    功能：
    1. 根据数据集自动选择评估指标
    2. 支持标准版单一分数和 LongBench-E 长度分桶
    3. 集成所有 LongBench 指标函数
    4. 预测结果后处理（特定数据集只取第一行）
    5. 正确传递 all_classes 给分类任务

    输入数据格式（来自 Generator）：
    {
        "query": str,
        "generated": str,          # 模型生成的答案
        "references": List[str],   # 标准答案列表
        "_dataset": str,           # 数据集名称
        "all_classes": List[str],  # 分类任务类别（可选）
        "length": int,             # 原始长度（LongBench-E 分桶用）
    }

    配置参数：
        - longbench_e_buckets: bool - 是否输出 LongBench-E 分桶分数
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.longbench_e_buckets = self.config.get("longbench_e_buckets", False)

        # 分数收集器（用于计算平均分）
        self._scores: list[float] = []
        self._dataset_scores: dict[str, list[float]] = {}

        # LongBench-E 分桶分数
        self._bucket_scores: dict[str, list[float]] = {
            "0-4k": [],
            "4-8k": [],
            "8k+": [],
        }

        # 时间收集器（支持所有数据集）
        self._refine_times: list[float] = []
        self._generate_times: list[float] = []
        self._retrieve_times: list[float] = []

    def _post_process_prediction(self, pred: str, dataset: str) -> str:
        """预测结果后处理"""
        # 对于特定数据集，只取第一行
        if dataset in LONGBENCH_FIRST_LINE_DATASETS:
            pred = pred.lstrip("\n").split("\n")[0]
        return pred

    def _get_length_bucket(self, length: int) -> str:
        """根据长度获取分桶名称"""
        if length < 4000:
            return "0-4k"
        elif length < 8000:
            return "4-8k"
        else:
            return "8k+"

    def _compute_score(
        self,
        pred: str,
        ground_truths: list[str],
        dataset: str,
        all_classes: list[str] | None = None,
    ) -> float:
        """计算单个样本的分数"""
        # 获取指标类型
        metric_type = LONGBENCH_DATASET_TO_METRIC.get(dataset, "qa_f1")
        metric_fn = LONGBENCH_METRIC_FUNCTIONS.get(metric_type, longbench_qa_f1_score)

        # 预处理预测结果
        pred = self._post_process_prediction(pred, dataset)

        # 对所有参考答案计算分数，取最高
        best_score = 0.0
        for ground_truth in ground_truths:
            try:
                score = metric_fn(pred, ground_truth, all_classes=all_classes or [])
                best_score = max(best_score, score)
            except Exception as e:
                self.logger.warning(f"Error computing score for {dataset}: {e}")

        return best_score

    def execute(self, data):
        """执行评估"""
        # Handle StopSignal - 输出汇总统计
        if isinstance(data, StopSignal):
            self._print_summary()
            return data

        # 获取必要字段
        dataset = data.get("_dataset", "unknown")
        pred = data.get("generated", "")
        references = data.get("references", [])
        all_classes = data.get("all_classes")
        length = data.get("length", 0)

        # 计算分数
        score = self._compute_score(pred, references, dataset, all_classes)

        # 分数 * 100（与原始 LongBench 一致）
        score_percent = round(score * 100, 2)

        # 收集分数
        self._scores.append(score)
        if dataset not in self._dataset_scores:
            self._dataset_scores[dataset] = []
        self._dataset_scores[dataset].append(score)

        # LongBench-E 分桶
        if self.longbench_e_buckets and length > 0:
            bucket = self._get_length_bucket(length)
            self._bucket_scores[bucket].append(score)

        # 打印单个样本分数和时间
        metric_type = LONGBENCH_DATASET_TO_METRIC.get(dataset, "qa_f1")

        # 计算单个 QA 的总时间
        total_qa_time = (
            data.get("retrieve_time", 0) + data.get("refine_time", 0) + data.get("generate_time", 0)
        )
        time_str = f" (time={total_qa_time:.3f}s)" if total_qa_time > 0 else ""
        print(f"\033[92m[LongBench {dataset}] {metric_type}: {score_percent}{time_str}\033[0m")

        # 将分数添加到数据中
        data["longbench_score"] = score
        data["longbench_score_percent"] = score_percent
        data["longbench_metric"] = metric_type

        # 收集时间数据（由 MapOperator 自动添加）
        if "refine_time" in data:
            self._refine_times.append(data["refine_time"])
        if "generate_time" in data:
            self._generate_times.append(data["generate_time"])
        if "retrieve_time" in data:
            self._retrieve_times.append(data["retrieve_time"])

        return data

    def _print_summary(self):
        """打印汇总统计"""
        if not self._scores:
            print("\n" + "=" * 80)
            print("No LongBench samples processed")
            print("=" * 80)
            return

        print("\n" + "=" * 80)
        print(f"LONGBENCH EVALUATION SUMMARY ({len(self._scores)} samples)")
        print("=" * 80)

        # 总体平均分
        avg_score = sum(self._scores) / len(self._scores) * 100
        print(f"\033[92m[Overall Average Score]: {avg_score:.2f}\033[0m")

        # 按数据集分组的平均分
        if self._dataset_scores:
            print("\n--- Per-Dataset Scores ---")
            for dataset, scores in sorted(self._dataset_scores.items()):
                avg = sum(scores) / len(scores) * 100
                metric_type = LONGBENCH_DATASET_TO_METRIC.get(dataset, "qa_f1")
                print(f"  {dataset} ({metric_type}): {avg:.2f} ({len(scores)} samples)")

        # LongBench-E 分桶分数
        if self.longbench_e_buckets:
            print("\n--- LongBench-E Length Buckets ---")
            for bucket, scores in self._bucket_scores.items():
                if scores:
                    avg = sum(scores) / len(scores) * 100
                    print(f"  {bucket}: {avg:.2f} ({len(scores)} samples)")

        # 时间统计（支持所有数据集）
        has_time_data = self._refine_times or self._generate_times or self._retrieve_times
        if has_time_data:
            print("\n--- Timing Statistics (seconds) ---")
            if self._retrieve_times:
                avg_retrieve = sum(self._retrieve_times) / len(self._retrieve_times)
                total_retrieve = sum(self._retrieve_times)
                print(
                    f"  Retrieve: avg={avg_retrieve:.3f}s, total={total_retrieve:.2f}s ({len(self._retrieve_times)} samples)"
                )
            if self._refine_times:
                avg_refine = sum(self._refine_times) / len(self._refine_times)
                total_refine = sum(self._refine_times)
                print(
                    f"  Refine:   avg={avg_refine:.3f}s, total={total_refine:.2f}s ({len(self._refine_times)} samples)"
                )
            if self._generate_times:
                avg_generate = sum(self._generate_times) / len(self._generate_times)
                total_generate = sum(self._generate_times)
                print(
                    f"  Generate: avg={avg_generate:.3f}s, total={total_generate:.2f}s ({len(self._generate_times)} samples)"
                )
            # 总时间
            total_time = (
                sum(self._retrieve_times) + sum(self._refine_times) + sum(self._generate_times)
            )
            print(f"  \033[92mTotal Pipeline Time: {total_time:.2f}s\033[0m")

        print("=" * 80 + "\n")

    def get_results(self) -> dict:
        """获取评估结果（用于程序化访问）"""
        results = {
            "overall_score": sum(self._scores) / len(self._scores) * 100 if self._scores else 0,
            "sample_count": len(self._scores),
            "per_dataset": {},
        }

        for dataset, scores in self._dataset_scores.items():
            results["per_dataset"][dataset] = {
                "score": sum(scores) / len(scores) * 100 if scores else 0,
                "count": len(scores),
                "metric": LONGBENCH_DATASET_TO_METRIC.get(dataset, "qa_f1"),
            }

        if self.longbench_e_buckets:
            results["buckets"] = {}
            for bucket, scores in self._bucket_scores.items():
                results["buckets"][bucket] = {
                    "score": sum(scores) / len(scores) * 100 if scores else 0,
                    "count": len(scores),
                }

        # 时间统计
        results["timing"] = {}
        if self._retrieve_times:
            results["timing"]["retrieve"] = {
                "avg": sum(self._retrieve_times) / len(self._retrieve_times),
                "total": sum(self._retrieve_times),
                "count": len(self._retrieve_times),
            }
        if self._refine_times:
            results["timing"]["refine"] = {
                "avg": sum(self._refine_times) / len(self._refine_times),
                "total": sum(self._refine_times),
                "count": len(self._refine_times),
            }
        if self._generate_times:
            results["timing"]["generate"] = {
                "avg": sum(self._generate_times) / len(self._generate_times),
                "total": sum(self._generate_times),
                "count": len(self._generate_times),
            }

        return results

    def __del__(self):
        """对象销毁时自动打印汇总（如果有数据）"""
        try:
            if self._scores:
                self._print_summary()
        except Exception:
            # 忽略析构时的错误
            pass
