"""
REFORM Context Compressor
==========================

基于REFORM论文的RAG上下文压缩算法实现。

核心思路：
1. 使用选定的attention heads构造token级别的cross-layer embeddings
2. 通过cosine similarity计算每个token对query的重要性
3. 选择高分tokens及其邻域片段，压缩上下文

实现特点：
- 支持 two-pass QKV 抽取（use_kv_cache=True）
- 支持 GQA 模型（Grouped Query Attention，如 Llama 3.x）
- 支持长上下文 chunking（128K tokens）
- 可配置的 span 合并策略和分隔符

注意：
    当前实现是 REFORM 风格的注意力头驱动 token 选取器，
    主要用于 RAG 场景的文本重构。
    完整的 REFORM 论文还包括 KV cache 压缩和 Recompute 步骤，
    这些功能已预留接口（见 model_utils.recompute_kv_cache）。

References:
    REFORM: Compress, Gather, and Recompute (Appendix B.5)
"""

import logging
from typing import Any

import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class REFORMCompressor:
    """REFORM风格的上下文压缩器

    使用预选的attention heads构造token embeddings，
    并基于query相关性进行智能压缩。

    实现详情：
    -----------
    - **Two-pass QKV 抽取**: 当 use_kv_cache=True 时，分别对 context 和 question
      做 forward，然后合并 QKV，避免 question 对 context attention 的干扰。

    - **GQA 安全头索引**: 对 K/V 头自动使用 modulo 操作，支持
      num_key_value_heads < num_attention_heads 的模型（如 Llama 3.x）。

    - **Span 合并优化**: 支持可配置的分隔符和真实 token 计数，
      避免 ' ... ' 引入额外 tokens。

    - **KV Recompute 接口**: 预留了 recompute_kv_cache 方法，
      可用于后续生成时的 KV cache 复用。
    """

    def __init__(
        self,
        model_extractor,
        selected_heads: list[dict[str, Any]],
        max_tokens: int = 2048,
        keep_prefix: int = 50,
        keep_suffix: int = 50,
        smoothing_window: int = 20,
        merge_threshold: int = 5,
        use_kv_cache: bool = True,
        enable_chunking: bool = True,
        chunk_size: int | None = None,
        question_reserve: int = 200,
        margin: int = 56,
        span_separator: str = "",
        recompute_token_count: bool = True,
    ):
        """初始化REFORM压缩器

        Args:
            model_extractor: AttentionHookExtractor实例，用于提取Q/K/V
            selected_heads: 选定的heads列表，每项包含{layer, head, type}
            max_tokens: 压缩后最大token数（全局预算）
            keep_prefix: 始终保留的前缀token数
            keep_suffix: 始终保留的后缀token数
            smoothing_window: 分数平滑窗口大小
            merge_threshold: 相邻token合并阈值
            use_kv_cache: 是否使用KV cache优化（two-pass QKV抽取）
            enable_chunking: 是否启用chunking模式（支持长上下文）
            chunk_size: Chunk大小，None则自动计算
            question_reserve: 每个chunk为question预留的token数
            margin: 安全边距token数
            span_separator: Span间分隔符（默认空字符串，可设为' ... '）
            recompute_token_count: 是否重新计算压缩后真实token数
        """
        self.model_extractor = model_extractor
        self.selected_heads = selected_heads
        self.max_tokens = max_tokens
        self.keep_prefix = keep_prefix
        self.keep_suffix = keep_suffix
        self.smoothing_window = smoothing_window
        self.merge_threshold = merge_threshold
        self.use_kv_cache = use_kv_cache
        self.enable_chunking = enable_chunking
        self.question_reserve = question_reserve
        self.margin = margin
        self.span_separator = span_separator
        self.recompute_token_count = recompute_token_count

        # Calculate chunk size based on model's max_position_embeddings (128K for Llama-3.1)
        max_len = (
            self.model_extractor.config.max_position_embeddings
            if hasattr(self.model_extractor.config, "max_position_embeddings")
            else 8192
        )
        self.chunk_size = chunk_size if chunk_size else (max_len - question_reserve - margin)

        logger.info(f"REFORMCompressor initialized with {len(selected_heads)} heads")
        logger.info(
            f"Compression params: max_tokens={max_tokens}, prefix={keep_prefix}, suffix={keep_suffix}"
        )
        logger.info(f"KV cache optimization: {'enabled' if use_kv_cache else 'disabled'}")
        logger.info(
            f"Chunking: {'enabled' if enable_chunking else 'disabled'}, chunk_size={self.chunk_size}"
        )

    def compress(
        self,
        context: str,
        question: str,
    ) -> dict[str, Any]:
        """压缩上下文（统一使用chunking流程）

        Args:
            context: 原始上下文文本（检索到的文档拼接）
            question: 问题文本

        Returns:
            {
                "compressed_context": str,
                "original_tokens": int,
                "compressed_tokens": int,
                "compression_rate": float,
                "num_spans": int,
                "num_chunks": int,
            }
        """
        logger.debug(
            f"REFORMCompressor.compress called with context length: {len(context)}, question: '{question[:50]}...'"
        )

        # Tokenize context
        context_tokens = self.model_extractor.tokenizer.encode(context, add_special_tokens=False)
        # Use unified chunking flow (short context = 1 chunk)
        logger.info(f"Processing {len(context_tokens)} tokens with chunk_size={self.chunk_size}")
        return self._compress_chunked(context, question, context_tokens)

    def _smooth_scores(self, scores: torch.Tensor, window: int) -> torch.Tensor:
        """平滑分数（滑动最大值）"""
        if window <= 1:
            return scores

        num_tokens = len(scores)
        smoothed = torch.zeros_like(scores)

        for i in range(num_tokens):
            start = max(0, i - window // 2)
            end = min(num_tokens, i + window // 2 + 1)
            smoothed[i] = scores[start:end].max()

        return smoothed

    def _compress_chunked(
        self,
        context: str,
        question: str,
        context_tokens: list[int],
    ) -> dict[str, Any]:
        """Chunked compression for long contexts

        Args:
            context: Full context text
            question: Question text
            context_tokens: Pre-tokenized context (for exact alignment)

        Returns:
            Compression result dict with num_chunks
        """
        logger.info(
            f"Starting chunked compression: {len(context_tokens)} tokens, chunk_size={self.chunk_size}"
        )

        # Step 1: Create chunks from token list
        chunks = self._create_chunks_from_tokens(context_tokens)
        logger.info(f"Created {len(chunks)} chunks")

        # Step 2: Process each chunk
        all_scores = []
        for i, chunk_info in enumerate(chunks):
            logger.debug(
                f"Processing chunk {i + 1}/{len(chunks)}: tokens {chunk_info['global_start']}-{chunk_info['global_end']}"
            )
            try:
                chunk_scores = self._process_chunk(chunk_info, question)
                all_scores.extend(chunk_scores)
                logger.debug(f"Chunk {i + 1} produced {len(chunk_scores)} scored tokens")
            except Exception as e:
                logger.error(f"Failed to process chunk {i + 1}: {e}", exc_info=True)
                # Continue with other chunks

        if not all_scores:
            logger.warning("No scores from any chunk, returning original context")
            return {
                "compressed_context": context,
                "original_tokens": len(context_tokens),
                "compressed_tokens": len(context_tokens),
                "compression_rate": 1.0,
                "num_spans": 1,
                "num_chunks": len(chunks),
            }

        # Step 3: Global top-k selection
        selected_tokens = self._global_top_k_selection(
            all_scores, total_context_tokens=len(context_tokens)
        )
        logger.info(f"Global top-k selected {len(selected_tokens)} tokens from {len(all_scores)}")

        # Step 4: Merge spans and decode (returns text and actual token count)
        compressed_context, actual_token_count = self._merge_spans_from_scores(selected_tokens)

        # Step 5: Statistics
        original_tokens = len(context_tokens)
        compressed_tokens = actual_token_count  # Use recomputed count
        compression_rate = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        # Count spans
        num_spans = 1
        for i in range(1, len(selected_tokens)):
            if selected_tokens[i][1] - selected_tokens[i - 1][1] > self.merge_threshold:
                num_spans += 1

        logger.info(
            f"Chunked compression: {original_tokens} → {compressed_tokens} tokens ({compression_rate:.2%}), {num_spans} spans, {len(chunks)} chunks"
        )
        logger.debug(
            f"Selected {len(selected_tokens)} tokens, recomputed to {actual_token_count} actual tokens"
        )

        return {
            "compressed_context": compressed_context,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_rate": compression_rate,
            "num_spans": num_spans,
            "num_chunks": len(chunks),
        }

    def _create_chunks_from_tokens(self, context_tokens: list[int]) -> list[dict]:
        """Create non-overlapping chunks from token list

        Args:
            context_tokens: Full context token IDs

        Returns:
            List of chunk info dicts with {tokens, global_start, global_end}
        """
        chunks = []
        for i in range(0, len(context_tokens), self.chunk_size):
            chunk_tokens = context_tokens[i : i + self.chunk_size]
            chunks.append(
                {"tokens": chunk_tokens, "global_start": i, "global_end": i + len(chunk_tokens)}
            )
        return chunks

    def _process_chunk(self, chunk_info: dict, question: str) -> list[tuple]:
        """Process one chunk with REFORM scoring

        使用 REFORM 风格的 two-pass QKV 抽取（如果启用 use_kv_cache）
        或传统的单次 forward（如果未启用）。

        Args:
            chunk_info: {tokens, global_start, global_end}
            question: Question text

        Returns:
            List of (score, global_pos, token_id) tuples (only for context tokens)
        """
        chunk_tokens = chunk_info["tokens"]
        global_offset = chunk_info["global_start"]

        # Step 1: Extract QKV components based on use_kv_cache setting
        if self.use_kv_cache:
            # Two-pass extraction: separate context and question forwards
            # Decode chunk tokens to text for two-pass extraction
            chunk_text = self.model_extractor.tokenizer.decode(
                chunk_tokens, skip_special_tokens=True
            )

            qkv_data, full_tokens, context_range, question_range = (
                self.model_extractor.extract_attention_components_with_kv(
                    context_text=chunk_text, question_text=question
                )
            )

            # Extract the context tokens from full_tokens (they were re-tokenized)
            context_tokens_retokenized = full_tokens[context_range[0] : context_range[1]]
            context_len = len(context_tokens_retokenized)
            seq_len = len(full_tokens)

            # Use re-tokenized context tokens for scoring (ensures alignment)
            scoring_context_tokens = context_tokens_retokenized
        else:
            # Traditional single-pass: concatenate and forward
            question_tokens = self.model_extractor.tokenizer.encode(
                f"\n\nQuestion: {question}", add_special_tokens=False
            )
            prompt_tokens = chunk_tokens + question_tokens
            qkv_data = self.model_extractor.extract_attention_from_token_ids(prompt_tokens)

            context_len = len(chunk_tokens)
            seq_len = len(prompt_tokens)

            # Use original chunk tokens for scoring
            scoring_context_tokens = chunk_tokens

        if not qkv_data:
            logger.warning(f"No QKV data for chunk at {global_offset}")
            return []

        # Step 2: Build embeddings for all tokens with GQA-safe head indexing
        num_kv_heads = self.model_extractor.num_key_value_heads

        embeddings_list = []
        for token_idx in range(seq_len):
            token_emb_list = []

            for head_config in self.selected_heads:
                layer_idx = head_config["layer"]
                head_idx = head_config["head"]
                head_type = head_config["type"].upper()

                if layer_idx not in qkv_data:
                    continue

                qkv = qkv_data[layer_idx]
                component_tensor = qkv[head_type]  # [batch, num_heads, seq_len, head_dim]

                # GQA-safe head indexing: K/V use fewer heads, need modulo
                if head_type in ["K", "V"]:
                    actual_head_idx = head_idx % num_kv_heads
                else:
                    actual_head_idx = head_idx

                # Extract head embedding for this token
                head_embed = component_tensor[0, actual_head_idx, token_idx, :]  # [head_dim]

                # L2 normalize
                head_embed_norm = F.normalize(head_embed.float(), p=2, dim=-1)
                token_emb_list.append(head_embed_norm)

            if token_emb_list:
                token_embedding = torch.cat(token_emb_list, dim=-1)  # [num_heads * head_dim]
                embeddings_list.append(token_embedding)

        if not embeddings_list:
            return []

        token_embeddings = torch.stack(embeddings_list, dim=0)  # [seq_len, embed_dim]

        # Step 3: Compute importance scores (only for context tokens)
        context_embs = token_embeddings[:context_len]  # [context_len, embed_dim]
        question_embs = token_embeddings[context_len:]  # [question_len, embed_dim]

        # Normalize
        context_embs = F.normalize(context_embs, p=2, dim=-1)
        question_embs = F.normalize(question_embs, p=2, dim=-1)

        # Cosine similarity: max over question tokens
        similarity = torch.mm(context_embs, question_embs.t())  # [context_len, question_len]
        raw_scores = similarity.max(dim=1).values  # [context_len]

        # Smooth scores
        smoothed_scores = self._smooth_scores(raw_scores, window=self.smoothing_window)

        # Step 4: Return scored tokens with global positions
        # Important: Use scoring_context_tokens (aligned with QKV extraction)
        # But need to map back to original global positions
        if len(scoring_context_tokens) != len(chunk_tokens):
            # Token count mismatch after re-tokenization (two-pass mode)
            # This can happen due to special tokens or encoding differences
            logger.warning(
                f"Token count mismatch at chunk {global_offset}: "
                f"original={len(chunk_tokens)}, re-tokenized={len(scoring_context_tokens)}"
            )
            # Use min to avoid index errors, scores will be truncated
            effective_len = min(context_len, len(chunk_tokens))
        else:
            effective_len = context_len

        scored_tokens = [
            (smoothed_scores[idx].item(), idx + global_offset, scoring_context_tokens[idx])
            for idx in range(effective_len)
        ]

        return scored_tokens

    def _global_top_k_selection(
        self, all_scores: list[tuple], total_context_tokens: int
    ) -> list[tuple]:
        """Select top-k tokens globally across all chunks

        Args:
            all_scores: List of (score, global_pos, token_id) from all chunks
            total_context_tokens: Total context token count (for prefix/suffix calculation)

        Returns:
            Selected tokens sorted by global position
        """
        # Separate prefix, middle, suffix
        prefix = [(s, p, t) for s, p, t in all_scores if p < self.keep_prefix]
        suffix = [
            (s, p, t) for s, p, t in all_scores if p >= total_context_tokens - self.keep_suffix
        ]
        middle = [
            (s, p, t)
            for s, p, t in all_scores
            if self.keep_prefix <= p < total_context_tokens - self.keep_suffix
        ]

        # Auto-keep prefix and suffix
        selected = prefix + suffix
        remaining_budget = self.max_tokens - len(selected)

        if remaining_budget <= 0:
            logger.warning(
                f"Prefix+suffix already exceed budget: {len(selected)} > {self.max_tokens}"
            )
            selected = selected[: self.max_tokens]
        else:
            # Select top-k from middle by score
            middle_sorted = sorted(middle, key=lambda x: x[0], reverse=True)
            selected.extend(middle_sorted[:remaining_budget])

        # Sort by global position for decoding
        selected.sort(key=lambda x: x[1])

        return selected

    def _merge_spans_from_scores(self, selected_tokens: list[tuple]) -> tuple[str, int]:
        """Merge scored tokens into spans and decode

        改进的span合并策略：
        1. 根据 merge_threshold 判断是否连续
        2. 使用可配置的分隔符拼接
        3. 重新计算真实token数（如果启用）

        Args:
            selected_tokens: List of (score, global_pos, token_id) sorted by position

        Returns:
            Tuple of (decoded compressed text, actual token count)
        """
        if not selected_tokens:
            return "", 0

        # Group into spans
        spans = []
        current_span = [selected_tokens[0][2]]  # Start with first token_id

        for i in range(1, len(selected_tokens)):
            prev_pos = selected_tokens[i - 1][1]
            curr_pos = selected_tokens[i][1]
            token_id = selected_tokens[i][2]

            if curr_pos - prev_pos <= self.merge_threshold:
                # Contiguous: extend current span
                current_span.append(token_id)
            else:
                # Gap: finalize current span, start new one
                if current_span:
                    spans.append(current_span)
                current_span = [token_id]

        # Finalize last span
        if current_span:
            spans.append(current_span)

        # Decode each span
        span_texts = []
        for span in spans:
            span_text = self.model_extractor.tokenizer.decode(span, skip_special_tokens=True)
            span_texts.append(span_text.strip())

        # Join with separator (空字符串或 ' ... ' 等)
        compressed_text = self.span_separator.join(span_texts)

        # Recompute actual token count if enabled
        if self.recompute_token_count:
            actual_tokens = self.model_extractor.tokenizer.encode(
                compressed_text, add_special_tokens=False
            )
            actual_token_count = len(actual_tokens)
        else:
            # Use selected token count
            actual_token_count = len(selected_tokens)

        return compressed_text, actual_token_count

    def recompute_kv_for_compressed_context(
        self,
        selected_token_ids: list[int],
    ) -> tuple[str, Any]:
        """为压缩后的上下文重新计算 KV cache（可选的 REFORM 优化）

        这是 REFORM 论文中的完整流程：
        1. 选出重要 tokens (compress)
        2. 重新 forward 获取新的 KV cache (recompute)
        3. 后续生成时使用压缩后的 KV cache

        当前 RAG 场景可能不需要这一步，但接口已预留。

        Args:
            selected_token_ids: 选出的 token IDs

        Returns:
            Tuple of (decoded_text, past_key_values)
        """
        return self.model_extractor.recompute_kv_cache(selected_token_ids)
