from collections import Counter
from typing import Any, Dict, List, Tuple, Union

from rouge import Rouge
from sage.core.api.function.map_function import MapFunction
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer


def _normalize_data(data: Union[Dict[str, Any], Tuple[Any, Any], str, Any]) -> Dict[str, Any]:
    """将上游数据标准化为评测期望的字典结构。

    兼容多种入参形态：
    - tuple: (user_query, generated_text)
    - dict: 直接透传（但保证必要键存在）
    - str/其他: 作为 generated 文本

    返回的字典至少包含：
    - 'generated': str
    - 'references': list[str]
    - 'question': str | None
    - 其余键原样保留
    """
    if isinstance(data, tuple):
        # 典型来自 OpenAIGenerator 的输出
        question = data[0] if len(data) > 0 else None
        generated = data[1] if len(data) > 1 else ""
        # 当 question 为字典且包含 references 时，提取为顶级 references（符合实际 pipeline 数据）
        references: List[str] = []
        if isinstance(question, dict):
            q_refs = question.get("references")
            if isinstance(q_refs, list):
                references = q_refs
            elif q_refs is not None:
                references = [str(q_refs)]
        return {
            "question": question,
            "generated": generated if isinstance(generated, str) else str(generated),
            "references": references,
        }

    if isinstance(data, dict):
        out = dict(data)
        out.setdefault("generated", out.get("pred", ""))

        # references 优先级：顶级 references（非空） > golds（非空） > question.references（非空） > []
        refs = out.get("references", None)

        def _to_list(val):
            if val is None:
                return []
            if isinstance(val, list):
                return val
            return [str(val)]

        # 顶级 references 是否有效（非空）
        refs_list = _to_list(refs)
        if len(refs_list) > 0:
            out["references"] = refs_list
        else:
            # 尝试 golds
            golds_list = _to_list(out.get("golds", []))
            if len(golds_list) > 0:
                out["references"] = golds_list
            else:
                # 尝试 question.references
                q = out.get("question")
                q_refs_list: List[str] = []
                if isinstance(q, dict):
                    q_refs_list = _to_list(q.get("references", []))
                out["references"] = q_refs_list

        # 确保 references 为列表
        if not isinstance(out.get("references", []), list):
            out["references"] = [str(out["references"])]
        return out

    # 其他类型，统一本为 generated 文本
    return {
        "question": None,
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
    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        
        if not golds or not pred:
            print(f"\033[93m[Acc] : 0.0000\033[0m")
            return nd
            
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
        return nd


class TokenCountEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        
        # 只计算refined_docs的token数（这是LongRefiner压缩后的文档）
        refined_docs = nd.get("refined_docs", [])
        total_tokens = 0
        
        if refined_docs:
            total_tokens = sum(len(str(doc).split()) for doc in refined_docs)
        
        print(f"\033[93m[Token Count] : {total_tokens}\033[0m")
        return nd


class LatencyEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        lat = nd.get("refine_time", 0.0) + nd.get("generate_time", 0.0)
        print(f"\033[93m[Latency] : {lat:.2f}s\033[0m")
        return nd


class ContextRecallEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        
        # Context Recall: 检查生成的答案是否包含了参考答案中的关键信息
        golds = nd.get("references", [])
        if not golds and "question" in nd:
            question_data = nd.get("question", {})
            if isinstance(question_data, dict):
                golds = question_data.get("references", [])
        
        pred = nd.get("generated", "")
        
        if not golds or not pred:
            print(f"\033[93m[Context Recall] : 0.0000\033[0m")
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
    def _count(self, docs):
        # 返回总 token 数，若为空返回 0（用于在 refine 为空时给出 0.00×）
        return sum(len(d.split()) for d in docs) if docs else 0

    def execute(self, data: dict):
        nd = _normalize_data(data)
        o = self._count(nd.get("retrieved_docs", []))
        r = self._count(nd.get("refined_docs", []))
        rate = (o / r) if r > 0 else 0.0
        print(f"\033[93m[Compression Rate] : {rate:.2f}×\033[0m")
        return nd
