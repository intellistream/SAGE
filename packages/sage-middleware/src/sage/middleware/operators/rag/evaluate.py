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
