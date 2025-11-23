"""
Model utilities for extracting attention components (Q, K, V) from transformer models.

This module provides hooks to capture query, key, and value tensors from
attention layers during forward passes.
"""

import logging
from collections import defaultdict
from typing import Any

import torch
import torch.nn as nn
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)


class AttentionHookExtractor:
    """Extract Q, K, V tensors from transformer attention layers using hooks."""

    def __init__(
        self,
        model_name: str,
        device: str = "cuda",
        dtype: str = "bfloat16",
        use_flash_attention: bool = False,
        layer_range: tuple[int, int] | None = None,
        cache_dir: str | None = None,
    ):
        """Initialize attention hook extractor.

        Args:
            model_name: HuggingFace model name
            device: Device to run model on
            dtype: Data type (bfloat16, float16, float32)
            use_flash_attention: Whether to use flash attention
            layer_range: Range of layers to extract (start, end), None for all
            cache_dir: Cache directory for models
        """
        self.model_name = model_name
        self.device = device
        self.dtype = self._get_dtype(dtype)
        self.use_flash_attention = use_flash_attention
        self.cache_dir = cache_dir

        # Load model and tokenizer
        logger.info(f"Loading model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir,
        )

        # Set padding token if not exists
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load config
        self.config = AutoConfig.from_pretrained(model_name, cache_dir=cache_dir)

        # Load model
        model_kwargs = {
            "torch_dtype": self.dtype,
            "device_map": device if device == "auto" else None,
            "cache_dir": cache_dir,
        }

        if use_flash_attention:
            model_kwargs["attn_implementation"] = "flash_attention_2"

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            **model_kwargs,
        )

        if device != "auto":
            self.model = self.model.to(device)

        self.model.eval()

        # Get model architecture info
        self.num_layers = self.config.num_hidden_layers
        self.num_heads = self.config.num_attention_heads
        self.hidden_size = self.config.hidden_size
        self.head_dim = self.hidden_size // self.num_heads

        # GQA support (Grouped Query Attention, e.g., Llama 3.x)
        self.num_key_value_heads = getattr(self.config, "num_key_value_heads", self.num_heads)
        # K/V use same head_dim as Q, just fewer heads
        self.kv_head_dim = self.head_dim

        # Set layer range
        if layer_range:
            self.layer_start, self.layer_end = layer_range
        else:
            self.layer_start, self.layer_end = 0, self.num_layers

        # Storage for extracted tensors
        self.attention_data = defaultdict(dict)
        self.hooks = []

        logger.info(f"Model loaded: {self.num_layers} layers, {self.num_heads} heads")

    def _get_dtype(self, dtype_str: str) -> torch.dtype:
        """Convert dtype string to torch dtype.

        Args:
            dtype_str: Data type string

        Returns:
            torch.dtype
        """
        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "fp16": torch.float16,
            "float32": torch.float32,
            "fp32": torch.float32,
        }
        return dtype_map.get(dtype_str.lower(), torch.bfloat16)

    def _get_attention_modules(self) -> list[tuple[int, nn.Module]]:
        """Get attention modules from the model.

        Returns:
            List of (layer_idx, attention_module) tuples
        """
        attention_modules = []

        # Try different model architectures
        if hasattr(self.model, "model"):
            # Most decoder models (LLaMA, Mistral, etc.)
            base_model = self.model.model
        elif hasattr(self.model, "transformer"):
            # GPT-2, GPT-Neo
            base_model = self.model.transformer
        else:
            base_model = self.model

        # Get layers
        if hasattr(base_model, "layers"):
            layers = base_model.layers
        elif hasattr(base_model, "h"):
            layers = base_model.h
        else:
            raise ValueError(f"Cannot find transformer layers in {self.model_name}")

        # Extract attention modules
        for layer_idx in range(self.layer_start, min(self.layer_end, len(layers))):
            layer = layers[layer_idx]

            # Find attention module
            if hasattr(layer, "self_attn"):
                attn_module = layer.self_attn
            elif hasattr(layer, "attn"):
                attn_module = layer.attn
            elif hasattr(layer, "attention"):
                attn_module = layer.attention
            else:
                logger.warning(f"Cannot find attention in layer {layer_idx}")
                continue

            attention_modules.append((layer_idx, attn_module))

        return attention_modules

    def register_hooks(self) -> None:
        """Register forward hooks to extract Q, K, V tensors."""
        attention_modules = self._get_attention_modules()

        for layer_idx, attn_module in attention_modules:

            def make_hook(layer_id):
                def hook(module, args, kwargs, output):
                    """Hook function to capture Q, K, V tensors."""
                    try:
                        # Extract hidden_states from kwargs (Llama 3.x style) or args (older models)
                        if "hidden_states" in kwargs:
                            hidden_states = kwargs["hidden_states"]
                        elif len(args) > 0:
                            hidden_states = args[0]
                        else:
                            return

                        # Try to get Q, K, V from module's forward computation
                        # This varies by architecture
                        if hasattr(module, "q_proj"):
                            # Standard transformer architecture
                            with torch.no_grad():
                                Q = module.q_proj(hidden_states)
                                K = module.k_proj(hidden_states)
                                V = module.v_proj(hidden_states)
                        elif hasattr(module, "qkv"):
                            # Packed QKV projection
                            with torch.no_grad():
                                qkv = module.qkv(hidden_states)
                                qkv = qkv.reshape(
                                    qkv.shape[0],
                                    qkv.shape[1],
                                    3,
                                    self.num_heads,
                                    self.head_dim,
                                )
                                Q, K, V = qkv.unbind(2)
                        else:
                            # Fallback: try to capture from output
                            return

                        # Reshape to [batch, num_heads, seq_len, head_dim]
                        batch_size, seq_len = hidden_states.shape[:2]

                        if Q.dim() == 3:
                            # Q: [batch, seq, hidden] -> [batch, num_heads, seq, head_dim]
                            Q = Q.reshape(batch_size, seq_len, self.num_heads, self.head_dim)
                            Q = Q.transpose(1, 2)  # [batch, heads, seq, dim]

                            # K, V might use GQA with fewer heads
                            K = K.reshape(
                                batch_size, seq_len, self.num_key_value_heads, self.kv_head_dim
                            )
                            V = V.reshape(
                                batch_size, seq_len, self.num_key_value_heads, self.kv_head_dim
                            )

                            K = K.transpose(1, 2)  # [batch, kv_heads, seq, dim]
                            V = V.transpose(1, 2)

                        # Store in cache
                        self.attention_data[layer_id] = {
                            "Q": Q.detach().cpu(),
                            "K": K.detach().cpu(),
                            "V": V.detach().cpu(),
                        }

                    except Exception as e:
                        logger.warning(f"Hook failed for layer {layer_id}: {e}")

                return hook

            # Register hook with kwargs support (for Llama 3.x and newer models)
            handle = attn_module.register_forward_hook(make_hook(layer_idx), with_kwargs=True)
            self.hooks.append(handle)

        logger.info(f"Registered {len(self.hooks)} attention hooks")

    def remove_hooks(self) -> None:
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()
        logger.info("Removed all hooks")

    def extract_attention_components(
        self,
        text: str | list[str],
        max_length: int = 8192,
    ) -> dict[int, dict[str, torch.Tensor]]:
        """Extract Q, K, V tensors for given text.

        Args:
            text: Input text or list of texts
            max_length: Maximum sequence length

        Returns:
            Dictionary mapping layer_idx to {"Q": tensor, "K": tensor, "V": tensor}
        """
        # Clear previous data
        self.attention_data.clear()

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Forward pass (hooks will capture Q, K, V)
        with torch.no_grad():
            _ = self.model(**inputs, output_attentions=False)

        return dict(self.attention_data)

    def extract_attention_components_with_kv(
        self,
        context_text: str,
        question_text: str,
        max_length: int = 8192,
    ) -> tuple[dict[int, dict[str, torch.Tensor]], list[int], tuple[int, int], tuple[int, int]]:
        """优化的注意力组件提取 - 分别编码context和question

        真正的REFORM优化策略:
        1. 分别编码context和question（两次短forward，而非一次长forward）
        2. Context forward获取context tokens的Q/K/V
        3. Question forward获取question tokens的Q/K/V
        4. 合并两者的Q/K/V数据

        这样的好处:
        - 两次短序列编码比一次长序列编码更快
        - 避免了question对context attention的干扰
        - 为后续可能的KV cache共享预留空间

        Returns:
            - qkv_data: Dictionary mapping layer_idx to {"Q": tensor, "K": tensor, "V": tensor}
            - tokens: Full token ids list
            - context_range: (start_idx, end_idx) for context
            - question_range: (start_idx, end_idx) for question
        """
        logger.debug("Starting optimized two-pass attention extraction...")

        # ============ Pass 1: Encode context only ============
        self.attention_data.clear()

        context_inputs = self.tokenizer(
            context_text,
            return_tensors="pt",
            truncation=True,
            max_length=max_length - 256,  # Reserve for question
            add_special_tokens=True,
        )
        context_tokens = context_inputs["input_ids"][0].tolist()
        context_inputs = {k: v.to(self.device) for k, v in context_inputs.items()}

        logger.debug(f"Pass 1: Encoding context ({len(context_tokens)} tokens)...")

        with torch.no_grad():
            _ = self.model(**context_inputs, output_attentions=False)

        # Save context QKV
        context_qkv = {k: v.copy() for k, v in self.attention_data.items()}
        logger.debug(f"Pass 1 complete: Extracted QKV for {len(context_qkv)} layers")

        # ============ Pass 2: Encode question only ============
        self.attention_data.clear()

        question_inputs = self.tokenizer(
            question_text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            add_special_tokens=True,
        )
        question_tokens = question_inputs["input_ids"][0].tolist()
        question_inputs = {k: v.to(self.device) for k, v in question_inputs.items()}

        logger.debug(f"Pass 2: Encoding question ({len(question_tokens)} tokens)...")

        with torch.no_grad():
            _ = self.model(**question_inputs, output_attentions=False)

        # Save question QKV
        question_qkv = {k: v.copy() for k, v in self.attention_data.items()}
        logger.debug(f"Pass 2 complete: Extracted QKV for {len(question_qkv)} layers")

        # ============ Pass 3: Merge QKV data ============
        merged_qkv = {}

        for layer_idx in context_qkv.keys():
            if layer_idx not in question_qkv:
                logger.warning(f"Layer {layer_idx} missing in question QKV")
                continue

            ctx = context_qkv[layer_idx]
            ques = question_qkv[layer_idx]

            # Concatenate along sequence dimension (dim=2)
            # Context: [batch, heads, ctx_len, head_dim]
            # Question: [batch, heads, ques_len, head_dim]
            # Merged: [batch, heads, ctx_len + ques_len, head_dim]
            merged_qkv[layer_idx] = {
                "Q": torch.cat([ctx["Q"], ques["Q"]], dim=2),
                "K": torch.cat([ctx["K"], ques["K"]], dim=2),
                "V": torch.cat([ctx["V"], ques["V"]], dim=2),
            }

        # Construct full token list (context tokens, then question tokens)
        full_tokens = context_tokens + question_tokens

        # Define ranges
        context_range = (0, len(context_tokens))
        question_range = (len(context_tokens), len(full_tokens))

        logger.debug(f"Merge complete: {len(merged_qkv)} layers, {len(full_tokens)} total tokens")
        logger.debug(f"Context: {context_range}, Question: {question_range}")

        return merged_qkv, full_tokens, context_range, question_range

    def get_model_info(self) -> dict[str, Any]:
        """Get model information.

        Returns:
            Dictionary with model info
        """
        return {
            "model_name": self.model_name,
            "num_layers": self.num_layers,
            "num_heads": self.num_heads,
            "hidden_size": self.hidden_size,
            "head_dim": self.head_dim,
            "device": self.device,
            "dtype": str(self.dtype),
            "layer_range": (self.layer_start, self.layer_end),
        }

    def extract_attention_from_token_ids(
        self,
        input_ids: list[int] | torch.Tensor,
    ) -> dict[int, dict[str, torch.Tensor]]:
        """Extract Q, K, V tensors from token IDs directly (avoid decode/encode).

        Args:
            input_ids: Token IDs as list or tensor [seq_len] or [batch, seq_len]

        Returns:
            Dictionary mapping layer_idx to {"Q": tensor, "K": tensor, "V": tensor}
        """
        # Clear previous data
        self.attention_data.clear()

        # Convert to tensor if needed
        if isinstance(input_ids, list):
            input_ids = torch.tensor([input_ids], dtype=torch.long)
        elif input_ids.dim() == 1:
            input_ids = input_ids.unsqueeze(0)

        input_ids = input_ids.to(self.device)

        # Forward pass (hooks will capture Q, K, V)
        with torch.no_grad():
            _ = self.model(input_ids=input_ids, output_attentions=False)

        return dict(self.attention_data)

    def recompute_kv_cache(
        self,
        selected_token_ids: list[int] | torch.Tensor,
    ) -> tuple[str, Any]:
        """Recompute KV cache for selected tokens (REFORM-style compression)

        这是 REFORM 论文中的 "Recompute" 步骤：
        1. 根据选出的 token IDs 重新构造输入
        2. 对这个新输入做一次 forward
        3. 返回新的 past_key_values （KV cache）

        这样做的好处：
        - 压缩后的 KV cache 更小，节省内存
        - 后续生成时可以复用这个 cache

        Args:
            selected_token_ids: Selected token IDs (list or tensor)

        Returns:
            Tuple of (decoded_text, past_key_values)
        """
        # Convert to tensor if needed
        if isinstance(selected_token_ids, list):
            input_ids = torch.tensor([selected_token_ids], dtype=torch.long)
        elif selected_token_ids.dim() == 1:
            input_ids = selected_token_ids.unsqueeze(0)
        else:
            input_ids = selected_token_ids

        input_ids = input_ids.to(self.device)

        # Decode for verification/logging
        decoded_text = self.tokenizer.decode(input_ids[0].tolist(), skip_special_tokens=True)

        # Forward pass with KV cache enabled
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                use_cache=True,  # Enable KV cache
                output_attentions=False,
            )

        # Extract past_key_values (KV cache)
        past_key_values = outputs.past_key_values

        logger.info(
            f"Recomputed KV cache for {input_ids.shape[1]} tokens ({len(past_key_values)} layers)"
        )

        return decoded_text, past_key_values


def create_model_extractor(cfg: Any) -> AttentionHookExtractor:
    """Create model extractor from configuration.

    Args:
        cfg: Configuration object

    Returns:
        AttentionHookExtractor instance
    """
    import torch

    # Auto-detect device if not specified
    if hasattr(cfg.model, "device") and cfg.model.device:
        device = cfg.model.device
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Auto-detected device: {device}")

    extractor = AttentionHookExtractor(
        model_name=cfg.model.name,
        device=device,
        dtype=cfg.model.get("dtype", "bfloat16"),
        use_flash_attention=cfg.model.get("use_flash_attention", False),
        layer_range=tuple(cfg.model.get("layer_range")) if cfg.model.get("layer_range") else None,
        cache_dir=cfg.model.get("cache_dir"),
    )

    # Register hooks
    extractor.register_hooks()

    logger.info(f"Model extractor created: {extractor.get_model_info()}")

    return extractor
