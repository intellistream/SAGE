import os
import json
import glob
from collections import Counter
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from rouge import Rouge

from sage.core.function.map_function import MapFunction


class BaseEvaluate(MapFunction):
    """基础评估类，提供数据加载功能"""
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}

        # 设置数据存储路径
        if hasattr(self.ctx, 'env_base_dir') and self.ctx.env_base_dir:
            self.states_dir = os.path.join(self.ctx.env_base_dir, ".sage_states")
        else:
            # 使用默认路径
            self.states_dir = os.path.join(os.getcwd(), ".sage_states")

        os.makedirs(self.states_dir, exist_ok=True)

    def _load_operator_data(self, operator_type):
        """加载指定算子类型的所有数据记录"""
        data_dir = os.path.join(self.states_dir, f"{operator_type}_data")
        if not os.path.exists(data_dir):
            return []

        all_records = []
        for filename in glob.glob(os.path.join(data_dir, "*.json")):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                    all_records.extend(records)
            except Exception as e:
                self.logger.error(f"Failed to load data from {filename}: {e}")

        return sorted(all_records, key=lambda x: x['timestamp'])

    def _load_operator_time(self, operator_name):
        """加载指定算子的时间记录"""
        time_dir = os.path.join(self.states_dir, operator_name)
        if not os.path.exists(time_dir):
            return []

        all_records = []
        for filename in glob.glob(os.path.join(time_dir, "*_time_*.json")):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                    all_records.extend(records)
            except Exception as e:
                self.logger.error(f"Failed to load time data from {filename}: {e}")

        return sorted(all_records, key=lambda x: x['timestamp'])


class F1Evaluate(BaseEvaluate):
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
        rec  = num_common / sum(r.values())
        return 2 * prec * rec / (prec + rec)

    def execute(self, data: dict):
        # 加载数据
        generator_records = self._load_operator_data("generator")
        if not generator_records:
            print("\033[93m[F1] : No data available\033[0m")
            return data

        # 计算每个问答对的F1分数
        scores = []
        for record in generator_records:
            pred = record['response']
            refs = data.get("references", [])  # 从原始数据中获取参考答案
            if refs:
                best = max(self._f1_score(pred, g) for g in refs)
                scores.append(best)

        # 计算平均F1分数
        avg_f1 = sum(scores) / len(scores) if scores else 0.0
        print(f"\033[93m[F1] : {avg_f1:.4f}\033[0m")
        return data


class RecallEvaluate(BaseEvaluate):
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
        # 从存储的数据中读取
        generator_records = self._load_operator_data("generator")
        if not generator_records:
            print("\033[93m[Recall] : No data available\033[0m")
            return data

        # 计算每个问答对的召回率
        scores = []
        for record in generator_records:
            pred = record['response']
            refs = data.get("references", [])  # 从原始数据中获取参考答案
            if refs:
                best = max(self._recall(pred, g) for g in refs)
                scores.append(best)

        # 计算平均召回率
        avg_recall = sum(scores) / len(scores) if scores else 0.0
        print(f"\033[93m[Recall] : {avg_recall:.4f}\033[0m")
        return data


class BertRecallEvaluate(BaseEvaluate):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.model = AutoModel.from_pretrained("bert-base-uncased")

    def execute(self, data: dict):
        # 从存储的数据中读取
        generator_records = self._load_operator_data("generator")
        if not generator_records:
            print("\033[93m[BertRecall] : No data available\033[0m")
            return data

        # 计算每个问答对的BERT召回率
        scores = []
        for record in generator_records:
            pred = record['response']
            refs = data.get("references", [])
            for g in refs:
                encs = self.tokenizer([pred, g], return_tensors="pt", padding=True)
                embs = self.model(**encs).last_hidden_state.mean(dim=1).detach().numpy()
                scores.append(float(cosine_similarity([embs[0]], [embs[1]])[0][0]))

        # 计算最佳分数
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BertRecall] : {best:.4f}\033[0m")
        return data


class RougeLEvaluate(BaseEvaluate):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        self.rouge = Rouge()

    def execute(self, data: dict):
        # 从存储的数据中读取
        generator_records = self._load_operator_data("generator")
        if not generator_records:
            print("\033[93m[ROUGE-L] : No data available\033[0m")
            return data

        # 计算每个问答对的ROUGE-L分数
        scores = []
        for record in generator_records:
            pred = record['response']
            refs = data.get("references", [])
            if refs:
                rouge_scores = [self.rouge.get_scores(pred, g)[0]["rouge-l"]["f"] for g in refs]
                scores.append(max(rouge_scores))

        # 计算平均分数
        avg_rouge = sum(scores) / len(scores) if scores else 0.0
        print(f"\033[93m[ROUGE-L] : {avg_rouge:.4f}\033[0m")
        return data


class BRSEvaluate(BaseEvaluate):
    def execute(self, data: dict):
        # 从存储的数据中读取
        generator_records = self._load_operator_data("generator")
        if not generator_records:
            print("\033[93m[BRS] : No data available\033[0m")
            return data

        # 计算每个问答对的BRS分数
        scores = []
        for record in generator_records:
            pred = record['response']
            refs = data.get("references", [])
            if refs:
                brs_scores = [(len(set(pred) & set(g)) / len(set(g))) if g else 0.0 for g in refs]
                scores.append(max(brs_scores))

        # 计算平均分数
        avg_brs = sum(scores) / len(scores) if scores else 0.0
        print(f"\033[93m[BRS] : {avg_brs:.4f}\033[0m")
        return data


class AccuracyEvaluate(BaseEvaluate):
    def execute(self, data: dict):
        # 从存储的数据中读取
        generator_records = self._load_operator_data("generator")
        if not generator_records:
            print("\033[93m[Acc] : No data available\033[0m")
            return data

        # 计算每个问答对的准确率
        scores = []
        for record in generator_records:
            pred = record['response']
            refs = data.get("references", [])
            if refs:
                correct = any(pred.strip() == g.strip() for g in refs)
                scores.append(float(correct))

        # 计算平均准确率
        avg_acc = sum(scores) / len(scores) if scores else 0.0
        print(f"\033[93m[Acc] : {avg_acc:.4f}\033[0m")
        return data


class TokenCountEvaluate(BaseEvaluate):
    def execute(self, data: dict):
        # 从存储的数据中读取
        generator_records = self._load_operator_data("generator")
        if not generator_records:
            print("\033[93m[Token Count] : No data available\033[0m")
            return data

        # 计算每个生成结果的token数量
        counts = []
        for record in generator_records:
            pred = record['response']
            count = len(pred.split())
            counts.append(count)

        # 计算平均token数量
        avg_count = sum(counts) / len(counts) if counts else 0
        print(f"\033[93m[Token Count] : {avg_count:.0f}\033[0m")
        return data


class LatencyEvaluate(BaseEvaluate):
    def _load_time_records(self):
        """加载所有时间记录"""
        time_dir = os.path.join(self.states_dir, "time_records")
        if not os.path.exists(time_dir):
            return []

        all_records = []
        for filename in glob.glob(os.path.join(time_dir, "*.json")):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                    all_records.extend(records)
            except Exception as e:
                self.logger.error(f"Failed to load time data from {filename}: {e}")

        return all_records

    def _get_function_times(self, time_records, function_class):
        """获取特定函数的所有时间记录"""
        return [r['duration'] for r in time_records if r['function_name'] == function_class]

    def execute(self, data: dict):
        # 加载所有时间记录
        time_records = self._load_time_records()

        if not time_records:
            print("\033[93m[Latency] : No time records available\033[0m")
            return data

        # 获取各个函数的时间记录
        refiner_times = self._get_function_times(time_records, "LongRefinerAdapter")
        generator_times = self._get_function_times(time_records, "OpenAIGenerator")
        retriever_times = self._get_function_times(time_records, "DenseRetriever")
        promptor_times = self._get_function_times(time_records, "QAPromptor")

        # 计算平均时间
        refiner_avg = sum(refiner_times) / len(refiner_times) if refiner_times else 0.0
        generator_avg = sum(generator_times) / len(generator_times) if generator_times else 0.0
        retriever_avg = sum(retriever_times) / len(retriever_times) if retriever_times else 0.0
        promptor_avg = sum(promptor_times) / len(promptor_times) if promptor_times else 0.0

        # 计算总延迟
        total_avg = refiner_avg + generator_avg + retriever_avg + promptor_avg

        # 打印详细的延迟信息
        print(f"\033[93m[Latency] : {total_avg:.2f}s total")
        print(f"  - Retriever: {retriever_avg:.2f}s")
        print(f"  - Refiner: {refiner_avg:.2f}s")
        print(f"  - Promptor: {promptor_avg:.2f}s")
        print(f"  - Generator: {generator_avg:.2f}s\033[0m")

        return data


class ContextRecallEvaluate(BaseEvaluate):
    def execute(self, data: dict):
        # 从存储的数据中读取
        retriever_records = self._load_operator_data("retriever")
        if not retriever_records:
            print("\033[93m[Context Recall] : No data available\033[0m")
            return data

        # 计算每个检索结果的上下文召回率
        scores = []
        for record in retriever_records:
            gold_ids = set(data["metadata"]["supporting_facts"]["sent_id"])
            ret_ids = set(data.get("retrieved_sent_ids", []))
            if gold_ids:
                rec = float(len(gold_ids & ret_ids) / len(gold_ids))
                scores.append(rec)

        # 计算平均上下文召回率
        avg_rec = sum(scores) / len(scores) if scores else 0.0
        print(f"\033[93m[Context Recall] : {avg_rec:.4f}\033[0m")
        return data


class CompressionRateEvaluate(BaseEvaluate):
    def _count(self, docs):
        if isinstance(docs, list):
            return sum(len(d.split()) for d in docs) or 1
        return len(docs.split()) or 1

    def execute(self, data: dict):
        # 加载数据
        refiner_records = self._load_operator_data("refiner")
        if not refiner_records:
            print("\033[93m[Compression Rate] : No data available\033[0m")
            return data

        # 计算每个文档的压缩率
        rates = []
        for record in refiner_records:
            input_size = self._count(record['input_docs'])
            refined_size = self._count(record['refined_docs'])
            rate = input_size / refined_size if refined_size else 1
            rates.append(rate)

        # 计算平均压缩率
        avg_rate = sum(rates) / len(rates) if rates else 1.0
        print(f"\033[93m[Compression Rate] : {avg_rate:.2f}×\033[0m")
        return data
