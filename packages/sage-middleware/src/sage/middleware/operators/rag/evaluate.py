from collections import Counter

from rouge import Rouge
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer

from sage.kernel.operators import MapOperator


class F1Evaluate(MapOperator):
    """F1分数评估器

    输入数据格式：{"query": str, "results": List[Any], "generated": str, "references": List[str]}
    """

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
        golds = data.get("references", [])
        pred = data.get("generated", "")
        best = max(self._f1_score(pred, g) for g in golds) if golds else 0.0
        print(f"\033[93m[F1] : {best:.4f}\033[0m")
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

    统计当前阶段文档的token数量
    优先级：refining_results（压缩后）> retrieval_results（原始）

    输入数据格式：{"query": str, "refining_results": List[str], ...} 或
                 {"query": str, "retrieval_results": List[Dict], ...}
    """

    def execute(self, data: dict):
        # 优先计算 refining_results（压缩后），其次是 retrieval_results（原始）
        docs = data.get("refining_results") or data.get("retrieval_results", [])
        total_tokens = 0

        if docs:
            for doc in docs:
                if isinstance(doc, dict):
                    text = doc.get("text", str(doc))
                    total_tokens += len(text.split())
                elif isinstance(doc, str):
                    total_tokens += len(doc.split())
                else:
                    total_tokens += len(str(doc).split())

        print(f"\033[93m[Token Count] : {total_tokens}\033[0m")
        return data


class LatencyEvaluate(MapOperator):
    """延迟评估器

    输入数据格式：{"query": str, "retrieve_time": float, "refine_time": float, "generate_time": float, ...}
    """

    def execute(self, data: dict):
        retrieve_time = data.get("retrieve_time", 0.0)
        refine_time = data.get("refine_time", 0.0)
        generate_time = data.get("generate_time", 0.0)
        total_lat = retrieve_time + refine_time + generate_time

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

    输入数据格式：{"query": str, "retrieval_results": List[Dict], "refining_results": List[str], ...}
    - retrieval_results: 原始检索的文档（用于计算原始token数）
    - refining_results: 压缩后的文档文本（用于计算压缩后token数）
    """

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

    def execute(self, data: dict):
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

        print(f"\033[93m[Compression Rate] : {compression_rate:.2f}×\033[0m")
        return data
