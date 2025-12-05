"""
核心的注意力头分析模块

整合了模型加载、Hook 注册、MNR 计算和头评估的所有核心功能
"""

import logging
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)


# ============================================================================
# 辅助函数
# ============================================================================


def normalize_text(text: str) -> str:
    """规范化文本用于 token 匹配

    在编码前进行规范化以提高答案 token 匹配的成功率。

    Args:
        text: 原始文本

    Returns:
        规范化后的文本（strip、lowercase、Unicode NFKC）
    """
    if not text:
        return ""

    # Strip 空白字符
    text = text.strip()

    # 转小写
    text = text.lower()

    # Unicode NFKC 规范化（处理各种 Unicode 变体）
    text = unicodedata.normalize("NFKC", text)

    return text


def find_subsequence(
    main_ids: list[int],
    sub_ids: list[int],
    start_from: int = 0,
) -> int:
    """在主序列中查找子序列的起始位置

    Args:
        main_ids: 主 token 序列
        sub_ids: 子 token 序列
        start_from: 从哪个位置开始查找

    Returns:
        子序列的起始索引，如果找不到返回 -1
    """
    if not sub_ids:
        return -1

    sub_len = len(sub_ids)
    main_len = len(main_ids)

    for i in range(start_from, main_len - sub_len + 1):
        if main_ids[i : i + sub_len] == sub_ids:
            return i

    return -1


def smooth_scores(
    scores: torch.Tensor,
    window_size: int = 41,
) -> torch.Tensor:
    """对分数应用局部最大值平滑

    根据 REFORM 论文，在计算 MNR 之前对 token 级别的相似度分数
    应用局部最大值平滑（窗口大小约41）。

    Args:
        scores: [context_len] 分数张量
        window_size: 平滑窗口大小

    Returns:
        平滑后的分数 [context_len]
    """
    if scores.dim() != 1:
        raise ValueError("scores must be 1D tensor")

    context_len = len(scores)
    smoothed = torch.zeros_like(scores)
    half_window = window_size // 2

    for i in range(context_len):
        start = max(0, i - half_window)
        end = min(context_len, i + half_window + 1)
        smoothed[i] = scores[start:end].max()

    return smoothed


# ============================================================================
# Part 1: 指标计算 (MNR)
# ============================================================================


def mean_normalized_rank(
    true_indices: list[int] | torch.Tensor | np.ndarray,
    predicted_scores: torch.Tensor | np.ndarray,
    normalize: bool = True,
) -> float:
    """计算平均归一化排名 (MNR)

    MNR 衡量预测分数对真实索引的排序能力。MNR 越低表示检索性能越好。

    Args:
        true_indices: 真实标签的索引
        predicted_scores: 所有 token 的预测相关性分数
        normalize: 是否按序列长度归一化

    Returns:
        Mean Normalized Rank (归一化后为 0-1，越低越好)
    """
    # 转换为 numpy
    if isinstance(predicted_scores, torch.Tensor):
        predicted_scores = predicted_scores.detach().cpu().numpy()
    if isinstance(true_indices, torch.Tensor):
        true_indices = true_indices.detach().cpu().numpy()
    if isinstance(true_indices, list):
        true_indices = np.array(true_indices)

    predicted_scores = np.asarray(predicted_scores).flatten()
    true_indices = np.asarray(true_indices).flatten()

    # 移除无效索引
    valid_mask = (true_indices >= 0) & (true_indices < len(predicted_scores))
    true_indices = true_indices[valid_mask]

    if len(true_indices) == 0:
        return 1.0  # 最差分数

    # 计算排名（分数越高，排名越靠前）
    sorted_indices = np.argsort(-predicted_scores)  # 降序
    ranks = np.argsort(sorted_indices)  # 每个位置的排名

    # 获取真实索引的排名
    true_ranks = ranks[true_indices]
    mean_rank = float(np.mean(true_ranks))

    # 归一化
    if normalize:
        seq_length = len(predicted_scores)
        return mean_rank / seq_length if seq_length > 0 else 1.0
    else:
        return mean_rank


class MetricsAggregator:
    """指标聚合器，用于累积多个样本的指标"""

    def __init__(self):
        self.values = defaultdict(list)
        self.count = 0

    def add(self, metrics: dict[str, float]) -> None:
        """添加一组指标"""
        for key, value in metrics.items():
            self.values[key].append(value)
        self.count += 1

    def compute_average(self) -> dict[str, float]:
        """计算平均值和标准差"""
        result = {}
        for key, values in self.values.items():
            if values:
                result[f"{key}"] = float(np.mean(values))
                result[f"{key}_std"] = float(np.std(values))
        return result

    def reset(self) -> None:
        """重置"""
        self.values.clear()
        self.count = 0


# ============================================================================
# Part 2: 模型加载和 Hook 注册
# ============================================================================


class AttentionHookExtractor:
    """注意力 Hook 提取器

    在 Transformer 模型的注意力层注册 forward hook，提取 Q/K/V 张量
    """

    def __init__(
        self,
        model_name: str,
        dtype: str = "bfloat16",
        device: str = "cuda",
        layer_range: tuple[int, int] | None = None,
    ):
        """初始化

        Args:
            model_name: 模型名称或路径
            dtype: 数据类型
            device: 设备
            layer_range: 要分析的层范围 [start, end)
        """
        self.model_name = model_name
        self.device = device
        self.dtype_str = dtype
        self.layer_range = layer_range

        # 加载模型
        logger.info(f"Loading model: {model_name}")
        self.dtype = self._get_dtype(dtype)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=self.dtype,
            device_map=device,
            trust_remote_code=True,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model.eval()

        # 获取注意力模块
        self.attention_modules = self._get_attention_modules()
        logger.info(f"Found {len(self.attention_modules)} attention layers")

        # Hook 存储
        self.hooks = []
        self.attention_outputs = {}  # {layer_idx: {"Q": tensor, "K": tensor, "V": tensor}}

    def _get_dtype(self, dtype_str: str) -> torch.dtype:
        """获取 torch dtype"""
        dtype_map = {
            "float32": torch.float32,
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }
        return dtype_map.get(dtype_str, torch.bfloat16)

    def _get_attention_modules(self) -> list[tuple[int, nn.Module]]:
        """获取所有注意力模块"""
        attention_modules = []

        # 支持 LLaMA/Mistral 架构
        if hasattr(self.model, "model") and hasattr(self.model.model, "layers"):
            layers = self.model.model.layers
            start_idx, end_idx = self.layer_range if self.layer_range else (0, len(layers))

            for idx in range(start_idx, min(end_idx, len(layers))):
                layer = layers[idx]
                if hasattr(layer, "self_attn"):
                    attention_modules.append((idx, layer.self_attn))
        else:
            raise ValueError(f"Unknown model architecture: {type(self.model)}")

        return attention_modules

    def register_hooks(self) -> None:
        """注册 forward hooks 提取 Q/K/V"""

        def make_hook(layer_id):
            def hook(module, args, kwargs, output):
                """提取 Q/K/V 张量"""
                # 从模块获取 Q/K/V 投影权重
                hidden_states = args[0] if args else kwargs.get("hidden_states")

                if hidden_states is None:
                    return output

                # 应用 Q/K/V 投影
                Q = module.q_proj(hidden_states)
                K = module.k_proj(hidden_states)
                V = module.v_proj(hidden_states)

                # Reshape 为 [batch, heads, seq_len, head_dim]
                batch_size, seq_len, _ = hidden_states.shape
                num_heads = module.num_heads
                head_dim = module.head_dim

                Q = Q.view(batch_size, seq_len, num_heads, head_dim).transpose(1, 2)
                K = K.view(batch_size, seq_len, num_heads, head_dim).transpose(1, 2)
                V = V.view(batch_size, seq_len, num_heads, head_dim).transpose(1, 2)

                # 存储
                self.attention_outputs[layer_id] = {
                    "Q": Q.detach(),
                    "K": K.detach(),
                    "V": V.detach(),
                }

                return output

            return hook

        # 为每个注意力层注册 hook
        for layer_idx, attn_module in self.attention_modules:
            handle = attn_module.register_forward_hook(make_hook(layer_idx), with_kwargs=True)
            self.hooks.append(handle)

        logger.info(f"Registered {len(self.hooks)} attention hooks")

    def remove_hooks(self) -> None:
        """移除所有 hooks"""
        for handle in self.hooks:
            handle.remove()
        self.hooks.clear()
        logger.info("Removed all hooks")

    def __call__(self, text: str) -> dict[int, dict[str, torch.Tensor]]:
        """运行模型并提取注意力"""
        self.attention_outputs.clear()

        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)

        with torch.no_grad():
            _ = self.model(**inputs)

        return self.attention_outputs


# ============================================================================
# Part 3: 头评估器
# ============================================================================


class HeadwiseEvaluator:
    """逐头评估器 - 评估每个注意力头的检索性能"""

    def __init__(
        self,
        model_extractor: AttentionHookExtractor,
        query_pooling: str = "max",
        context_pooling: str = "mean",
        output_top_k: int = 20,
    ):
        """初始化

        Args:
            model_extractor: 模型提取器
            query_pooling: 查询池化方法 ("max", "mean", "last")
            context_pooling: 上下文池化方法 ("mean", "max", "first")
            output_top_k: 输出 top-k 个头
        """
        self.model_extractor = model_extractor
        self.query_pooling = query_pooling
        self.context_pooling = context_pooling
        self.output_top_k = output_top_k

        # 存储每个头的指标
        self.head_metrics = defaultdict(lambda: MetricsAggregator())

        logger.info("Evaluator initialized (Q/K/V heads)")

    def _pool_vectors(
        self,
        vectors: torch.Tensor,
        pooling_method: str,
        indices: list[int] | None = None,
    ) -> torch.Tensor:
        """池化向量

        Args:
            vectors: [batch, heads, seq_len, dim] 或 [batch, heads, dim]
            pooling_method: 池化方法
            indices: 特定位置索引

        Returns:
            [batch, heads, dim]
        """
        if indices is not None and len(indices) > 0:
            if vectors.dim() == 4:
                vectors = vectors[:, :, indices, :]

        if vectors.dim() == 4 and vectors.shape[2] == 0:
            batch, heads, _, dim = vectors.shape
            return torch.zeros(batch, heads, dim, device=vectors.device, dtype=vectors.dtype)

        if vectors.dim() == 3:
            return vectors

        # 在序列维度池化
        if pooling_method == "mean":
            return vectors.mean(dim=2)
        elif pooling_method == "max":
            return vectors.max(dim=2)[0]
        elif pooling_method == "first":
            return vectors[:, :, 0, :]
        elif pooling_method == "last":
            return vectors[:, :, -1, :]
        else:
            raise ValueError(f"Unknown pooling: {pooling_method}")

    def _compute_similarity(
        self,
        query_vecs: torch.Tensor,
        context_vecs: torch.Tensor,
    ) -> torch.Tensor:
        """计算相似度 (带 query 维度 max pooling)

        对每个 context token i: score[i] = max_j cosine(context[i], query[j])

        Args:
            query_vecs: [batch, heads, query_len, dim]
            context_vecs: [batch, heads, context_len, dim]

        Returns:
            [batch, heads, context_len]
        """
        # 转换为 float32 提高数值稳定性
        if query_vecs.dtype == torch.bfloat16:
            query_vecs = query_vecs.float()
        if context_vecs.dtype == torch.bfloat16:
            context_vecs = context_vecs.float()

        # 归一化
        query_vecs = F.normalize(query_vecs, p=2, dim=-1)
        context_vecs = F.normalize(context_vecs, p=2, dim=-1)

        # [batch, heads, context_len, query_len]
        pairwise = torch.matmul(context_vecs, query_vecs.transpose(-2, -1))

        # Max pooling over query dimension
        similarity = pairwise.max(dim=-1)[0]  # [batch, heads, context_len]

        return similarity

    def evaluate_sample(
        self,
        question: str,
        context: str,
        answers: list[str],
    ) -> dict[str, dict[str, float]]:
        """评估单个样本

        根据 REFORM 论文，只将 ground-truth 答案 span 作为正样本 token，
        而不是所有 context tokens。

        Args:
            question: 问题
            context: 上下文
            answers: ground-truth 答案列表

        Returns:
            {(layer, head, type): {"mnr": float}}
        """
        # 构建输入（不添加 "Question:" 和 "Context:" 前缀，以便 token 对齐）
        combined_text = f"{question}\n\n{context}"

        # 规范化文本用于答案匹配
        question_norm = normalize_text(question)
        context_norm = normalize_text(context)
        answers_norm = [normalize_text(ans) for ans in answers]

        # 提取注意力
        attention_outputs = self.model_extractor(combined_text)

        # Tokenize 获取位置（使用规范化后的文本以便对齐）
        combined_text_norm = f"{question_norm}\n\n{context_norm}"
        inputs = self.model_extractor.tokenizer(combined_text_norm, return_tensors="pt")
        input_ids = inputs["input_ids"][0].tolist()

        # 分别 tokenize question 和 context（不添加特殊 token，使用规范化文本）
        question_tokens = self.model_extractor.tokenizer.encode(
            question_norm, add_special_tokens=False
        )
        context_tokens = self.model_extractor.tokenizer.encode(
            context_norm, add_special_tokens=False
        )

        # 使用子序列查找确定准确位置
        question_start = find_subsequence(input_ids, question_tokens)
        if question_start == -1:
            logger.warning("Could not find question tokens in combined sequence")
            return {}

        context_start = find_subsequence(input_ids, context_tokens, start_from=question_start + 1)
        if context_start == -1:
            logger.warning("Could not find context tokens in combined sequence")
            return {}

        question_indices = list(range(question_start, question_start + len(question_tokens)))
        context_indices = list(range(context_start, context_start + len(context_tokens)))

        if not question_indices or not context_indices:
            return {}

        # 查找答案 span 在 context 中的位置（相对于 context_indices）
        answer_token_indices = set()
        for answer_norm in answers_norm:
            if not answer_norm:
                continue

            # Tokenize 答案（使用规范化文本）
            answer_tokens = self.model_extractor.tokenizer.encode(
                answer_norm, add_special_tokens=False
            )
            if not answer_tokens:
                continue

            # 在 input_ids 中查找答案（只在 context 范围内）
            search_start = context_start
            while search_start < context_start + len(context_tokens):
                match_pos = find_subsequence(input_ids, answer_tokens, start_from=search_start)
                if match_pos == -1 or match_pos >= context_start + len(context_tokens):
                    break

                # 记录答案 span 的所有位置（相对于 context_indices）
                for i in range(len(answer_tokens)):
                    abs_idx = match_pos + i
                    if abs_idx in context_indices:
                        rel_idx = abs_idx - context_start
                        answer_token_indices.add(rel_idx)

                search_start = match_pos + 1

        # 如果找不到答案，跳过此样本
        if not answer_token_indices:
            logger.warning(f"No answer spans found in context for answers: {answers}")
            # 返回默认 MNR=1.0
            results = {}
            for layer_idx in attention_outputs.keys():
                for head_type in ["Q", "K", "V"]:
                    num_heads = attention_outputs[layer_idx][head_type].shape[1]
                    for head_idx in range(num_heads):
                        key = (layer_idx, head_idx, head_type)
                        results[key] = {"mnr": 1.0}
            return results

        true_indices = sorted(answer_token_indices)

        results = {}

        # 评估每一层的每个头的每种类型
        for layer_idx, layer_data in attention_outputs.items():
            for head_type in ["Q", "K", "V"]:
                vecs = layer_data[head_type]  # [batch, heads, seq_len, dim]

                # 提取 query 和 context 向量
                query_vecs = vecs[:, :, question_indices, :]
                context_vecs = vecs[:, :, context_indices, :]

                # 计算相似度
                similarity = self._compute_similarity(
                    query_vecs, context_vecs
                )  # [batch, heads, context_len]

                # 对每个头计算 MNR
                num_heads = similarity.shape[1]
                for head_idx in range(num_heads):
                    head_sim = similarity[0, head_idx, :]  # [context_len]

                    # 应用局部平滑（REFORM 论文中的方法）
                    head_sim = smooth_scores(head_sim, window_size=41)

                    # 使用答案 span 作为 true_indices（而非所有 context tokens）
                    mnr = mean_normalized_rank(true_indices, head_sim, normalize=True)

                    key = (layer_idx, head_idx, head_type)
                    results[key] = {"mnr": mnr}

        return results

    def evaluate_samples(
        self,
        samples: list[dict],
        log_interval: int = 10,
    ) -> pd.DataFrame:
        """评估多个样本

        Args:
            samples: [{"question": str, "context": str, "answers": list}, ...]
            log_interval: 日志间隔

        Returns:
            DataFrame with columns: layer, head, head_type, mnr, mnr_std
        """
        logger.info(f"Evaluating {len(samples)} samples...")

        for idx, sample in enumerate(tqdm(samples, desc="Evaluating heads")):
            question = sample["question"]
            context = sample["context"]
            answers = sample.get("answers", [])

            # 评估样本
            results = self.evaluate_sample(question, context, answers)

            # 累积指标
            for (layer, head, head_type), metrics in results.items():
                key = f"L{layer}_H{head}_{head_type}"
                self.head_metrics[key].add(metrics)

            if (idx + 1) % log_interval == 0:
                logger.info(f"Processed {idx + 1}/{len(samples)} samples")

        # 汇总结果
        logger.info("Computing final statistics...")
        rows = []
        for key, aggregator in self.head_metrics.items():
            # 解析 key: L14_H6_Q
            parts = key.split("_")
            layer = int(parts[0][1:])
            head = int(parts[1][1:])
            head_type = parts[2]

            stats = aggregator.compute_average()
            rows.append(
                {
                    "layer": layer,
                    "head": head,
                    "head_type": head_type,
                    "mnr": stats.get("mnr", 1.0),
                    "mnr_std": stats.get("mnr_std", 0.0),
                }
            )

        df = pd.DataFrame(rows)
        df = df.sort_values("mnr")  # 按 MNR 升序排列

        return df

    def get_top_heads(self, results_df: pd.DataFrame, top_k: int | None = None) -> pd.DataFrame:
        """获取 top-k 个头"""
        if top_k is None:
            top_k = self.output_top_k
        return results_df.head(top_k)

    def save_results(self, results_df: pd.DataFrame, output_dir: Path, dataset_name: str) -> None:
        """保存结果"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存所有结果
        csv_path = output_dir / f"head_mnr_{dataset_name}_all_types.csv"
        results_df.to_csv(csv_path, index=False)
        logger.info(f"Saved results to {csv_path}")

        # 保存 top-k
        top_heads = self.get_top_heads(results_df)
        top_csv_path = output_dir / f"head_mnr_{dataset_name}_top{self.output_top_k}.csv"
        top_heads.to_csv(top_csv_path, index=False)
        logger.info(f"Saved top-{self.output_top_k} heads to {top_csv_path}")
