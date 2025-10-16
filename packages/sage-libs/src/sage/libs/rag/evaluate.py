from collections import Counter
from typing import Any, Dict, Tuple, Union

from rouge import Rouge
from sage.kernel.api.function.map_function import MapFunction
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer


def _normalize_data(
    data: Union[Dict[str, Any], Tuple[Any, Any], str, Any],
) -> Dict[str, Any]:
    """将上游数据标准化为评测期望的字典结构。

    兼容多种入参形态：
    - dict: 直接使用（标准格式）
    - tuple: (user_query, generated_text) - 旧格式兼容
    - str/其他: 作为 generated 文本

    返回的字典至少包含：
    - 'generated': str
    - 'references': list[str]
    - 其余键原样保留
    """
    if isinstance(data, dict):
        # 标准格式，直接返回
        return data

    if isinstance(data, tuple):
        # 旧的 tuple 格式兼容: (user_query, generated_text)
        question = data[0] if len(data) > 0 else None
        generated = data[1] if len(data) > 1 else ""
        return {
            "query": question,
            "generated": generated if isinstance(generated, str) else str(generated),
            "references": [],
        }

    # 其他类型，统一作为 generated 文本
    return {
        "query": None,
        "generated": data if isinstance(data, str) else str(data),
        "references": [],
    }


class F1Evaluate(MapFunction):
    def _get_tokens(self, text: str):
        return text.lower().split()

    def _f1_score(self, pred: str, ref: str):
        r = Counter(self._get_tokens(ref))
        p = Counter(self._get_tokens(pred))
        common = r & p
        if not r or not p:
            return float(r == p)
        num_common = sum(common.values())
        if num_common == 0:
            return 0.0
        prec = num_common / sum(p.values())
        rec = num_common / sum(r.values())
        return 2 * prec * rec / (prec + rec)

    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        best = max(self._f1_score(pred, g) for g in golds) if golds else 0.0
        print(f"\033[93m[F1] : {best:.4f}\033[0m")
        return nd


class RecallEvaluate(MapFunction):
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
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        best = max(self._recall(pred, g) for g in golds) if golds else 0.0
        print(f"\033[93m[Recall] : {best:.4f}\033[0m")
        return nd


class BertRecallEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.model = AutoModel.from_pretrained("bert-base-uncased")

    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        scores = []
        for g in golds:
            encs = self.tokenizer([pred, g], return_tensors="pt", padding=True)
            embs = self.model(**encs).last_hidden_state.mean(dim=1).detach().numpy()
            scores.append(float(cosine_similarity([embs[0]], [embs[1]])[0][0]))
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BertRecall] : {best:.4f}\033[0m")
        return nd


class RougeLEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.rouge = Rouge()

    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        scores = [self.rouge.get_scores(pred, g)[0]["rouge-l"]["f"] for g in golds]
        best = max(scores) if scores else 0.0
        print(f"\033[93m[ROUGE-L] : {best:.4f}\033[0m")
        return nd


class BRSEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        scores = [(len(set(pred) & set(g)) / len(set(g))) if g else 0.0 for g in golds]
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BRS] : {best:.4f}\033[0m")
        return nd


class AccuracyEvaluate(MapFunction):
    def _normalize_text(self, text: str) -> str:
        """标准化文本用于比较"""
        return text.lower().strip()

    def execute(self, data: dict):
        nd = _normalize_data(data)

        # 获取参考答案
        golds = nd.get("references", [])
        pred = nd.get("generated", "")

        if not golds or not pred:
            print("\033[93m[Acc] : 0.0000\033[0m")
            return nd

        pred_norm = self._normalize_text(pred)

        # 准确率：检查预测答案是否与任一参考答案匹配
        correct = False
        for gold in golds:
            gold_norm = self._normalize_text(gold)
            gold_words = set(gold_norm.split())
            pred_words = set(pred_norm.split())
            # 如果预测答案包含参考答案中的重要词汇，认为是正确的
            if gold_words and len(gold_words & pred_words) / len(gold_words) >= 0.3:
                correct = True
                break

        print(f"\033[93m[Acc] : {float(correct):.4f}\033[0m")
        return nd


class TokenCountEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)

        # 按优先级获取文档
        docs = nd.get("refining_docs") or nd.get("reranking_docs") or nd.get("retrieval_docs")

        if not docs:
            print("\033[92m[Token Count] : 0\033[0m")
            return nd

        # 计算总token数（简单估算：字符数/4）
        total_tokens = sum(len(doc) // 4 for doc in docs)
        print(f"\033[92m[Token Count] : {total_tokens}\033[0m")
        return nd


class LatencyEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        lat = nd.get("refining_time", 0.0) + nd.get("generation_time", 0.0)
        print(f"\033[93m[Latency] : {lat:.2f}s\033[0m")
        return nd


class ContextRecallEvaluate(MapFunction):
    def _normalize_text(self, text: str) -> str:
        """标准化文本用于比较"""
        return text.lower().strip()

    def execute(self, data: dict):
        nd = _normalize_data(data)

        # Context Recall: 检查生成的答案是否包含了参考答案中的关键信息
        golds = nd.get("references", [])
        pred = nd.get("generated", "")

        if not golds or not pred:
            print("\033[93m[Context Recall] : 0.0000\033[0m")
            return nd

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
        return nd


class CompressionRateEvaluate(MapFunction):
    def _count_tokens(self, docs):
        """计算文档列表的总token数"""
        if not docs:
            return 0
        return sum(len(str(d).split()) for d in docs)

    def execute(self, data: dict):
        nd = _normalize_data(data)

        # 获取原始检索文档的token数
        retrieval_docs = nd.get("retrieval_docs", [])
        retrieved_tokens = self._count_tokens(retrieval_docs)

        # 获取refiner压缩后的文档token数
        refining_docs = nd.get("refining_docs", [])
        refined_tokens = self._count_tokens(refining_docs)

        # 计算压缩率
        if refined_tokens > 0:
            compression_rate = retrieved_tokens / refined_tokens
        else:
            compression_rate = 0.0

        print(f"\033[93m[Compression Rate] : {compression_rate:.2f}×\033[0m")
        return nd
